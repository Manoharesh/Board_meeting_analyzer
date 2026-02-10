import json
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request

import numpy as np

from app.ai.action_items import extract_action_items
from app.ai.decision_extractor import extract_decisions
from app.ai.llm_client import call_llm
from app.ai.sentiment import get_sentiment_breakdown, track_speaker_sentiment
from app.ai.summarizer import summarize
from app.ai.topic_query import query_by_topic, semantic_query as semantic_query_fallback
from app.config import config
from app.transcription.realtime_stt import transcribe_audio

logger = logging.getLogger(__name__)


class MeetingOrchestrator:
    def __init__(self) -> None:
        self._use_langchain = bool(getattr(config, "ORCHESTRATION_USE_LANGCHAIN", True))
        self._n8n_webhook_url = str(getattr(config, "N8N_WEBHOOK_URL", "") or "").strip()
        self._n8n_timeout = float(getattr(config, "N8N_TIMEOUT_SECONDS", 2.5))
        self._llm_timeout = float(getattr(config, "LLM_TIMEOUT_SECONDS", 30.0))
        self._transcript_cache: Dict[str, Dict[str, Any]] = {}
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}
        self._qa_cache: Dict[Tuple[str, str, int, str], Dict[str, Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)

    def process_audio_chunk(self, audio_data: np.ndarray, speaker_name: str) -> Dict[str, Any]:
        success, transcription = transcribe_audio(audio_data)
        if not success or not transcription:
            transcription = "[Transcription failed]"

        sentiment = track_speaker_sentiment(speaker_name, transcription)
        return {
            "transcription": transcription,
            "sentiment": sentiment,
        }

    def process_text_chunk(self, speaker_name: str, text: str) -> Dict[str, Any]:
        return track_speaker_sentiment(speaker_name, text)

    def query_topic(self, chunks: List[Dict[str, Any]], topic: str) -> List[Dict[str, Any]]:
        return query_by_topic(chunks, topic)

    def semantic_query(
        self,
        meeting_id: str,
        chunks: List[Dict[str, Any]],
        query: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], str]:
        artifact = self._get_transcript_artifact(meeting_id, chunks, metadata)
        query_value = (query or "").strip()

        if not chunks:
            if metadata and metadata.get("status") == "no_audio":
                return [], "I didn’t receive any audio input for this meeting, so I can’t answer questions about the discussion."
            return [], "No transcript yet. You can still ask questions."

        if not query_value:
            return list(chunks), artifact["transcript_text"]

        cache_key = ("semantic", meeting_id, artifact["chunk_count"], query_value.lower())
        cached = self._qa_cache.get(cache_key)
        if cached:
            return list(cached.get("relevant_chunks", [])), str(cached.get("answer", ""))

        relevant_chunks = self._select_relevant_chunks(chunks, query_value)
        
        try:
            future = self._executor.submit(
                self._run_json_chain,
                system_message="You are a board meeting assistant. Answer only from the provided transcript context.",
                context_message=artifact["context_message"],
                user_message=query_value,
                response_schema={"answer": "string"},
            )
            payload = future.result(timeout=self._llm_timeout)
            answer = self._extract_text(payload, ("answer", "response", "result"))
        except FutureTimeoutError:
            logger.warning("Semantic query timed out for: %s", query_value[:50])
            answer = ""
        except Exception as exc:
            logger.error("Error in semantic_query: %s", exc)
            answer = ""

        if not answer:
            fallback_chunks, fallback_answer = semantic_query_fallback(chunks, query_value)
            if fallback_chunks:
                relevant_chunks = fallback_chunks
            answer = str(fallback_answer or "").strip()

        if not answer:
            answer = "I could not find enough detail in the transcript to answer that."

        self._qa_cache[cache_key] = {
            "relevant_chunks": list(relevant_chunks),
            "answer": answer,
        }
        return relevant_chunks, answer

    def ask_question(
        self,
        meeting_id: str,
        chunks: List[Dict[str, Any]],
        question: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        artifact = self._get_transcript_artifact(meeting_id, chunks, metadata)
        question_value = (question or "").strip()

        if not chunks:
            if metadata and metadata.get("status") == "no_audio":
                return "I didn’t receive any audio input for this meeting, so I can’t provide any details."
            return "No transcript yet. You can still ask questions."

        if not question_value:
            return artifact["transcript_text"]

        cache_key = ("ask", meeting_id, artifact["chunk_count"], question_value.lower())
        cached = self._qa_cache.get(cache_key)
        if cached:
            return str(cached.get("answer", ""))

        try:
            future = self._executor.submit(
                self._run_json_chain,
                system_message="You are a board meeting assistant. Answer only from the provided transcript context.",
                context_message=artifact["context_message"],
                user_message=question_value,
                response_schema={"answer": "string"},
            )
            payload = future.result(timeout=self._llm_timeout)
            answer = self._extract_text(payload, ("answer", "response", "result"))
        except FutureTimeoutError:
            logger.warning("LLM call timed out for question: %s", question_value[:50])
            answer = ""
        except Exception as exc:
            logger.error("Error in ask_question: %s", exc)
            answer = ""

        if not answer:
            _, fallback_answer = semantic_query_fallback(chunks, question_value)
            answer = str(fallback_answer or "").strip()

        if not answer:
            answer = "I could not find enough detail in the transcript to answer that."

        self._qa_cache[cache_key] = {"answer": answer}
        return answer

    def analyze_meeting(
        self,
        meeting_id: str,
        chunks: List[Dict[str, Any]],
        full_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        artifact = self._get_transcript_artifact(meeting_id, chunks, metadata)
        cached = self._analysis_cache.get(meeting_id)
        if cached and cached.get("chunk_count") == artifact["chunk_count"]:
            return dict(cached.get("payload", {}))

        summary_overview, key_points, sentiment_breakdown = self._summarize_with_sentiment(
            chunks=chunks,
            artifact=artifact,
        )
        decisions = extract_decisions(full_text) if full_text else []
        action_items = extract_action_items(full_text) if full_text else []

        merged_points: List[str] = []
        if summary_overview:
            merged_points.append(summary_overview)
        for point in key_points:
            normalized = str(point).strip()
            if normalized and normalized not in merged_points:
                merged_points.append(normalized)

        payload = {
            "meeting_id": meeting_id,
            "summary": artifact["transcript_text"],
            "key_points": merged_points,
            "decisions": decisions,
            "action_items": action_items,
            "sentiment_breakdown": sentiment_breakdown,
            "speakers": artifact["speakers"],
        }

        self._analysis_cache[meeting_id] = {
            "chunk_count": artifact["chunk_count"],
            "payload": payload,
        }
        self._emit_n8n_event(
            "meeting.analysis.completed",
            {
                "meeting_id": meeting_id,
                "chunk_count": artifact["chunk_count"],
                "speaker_count": len(artifact["speakers"]),
            },
        )
        return payload

    def _summarize_with_sentiment(
        self,
        chunks: List[Dict[str, Any]],
        artifact: Dict[str, Any],
        length: str = "short",
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        sentiment_breakdown = get_sentiment_breakdown()
        if not chunks:
            return "", [], sentiment_breakdown

        summary_result = summarize(chunks, length=length)
        summary = ""
        key_points: List[str] = []

        if isinstance(summary_result, dict):
            summary = str(summary_result.get("summary") or "").strip()
            key_points = self._extract_list(summary_result, "key_points")
        elif summary_result:
            summary = str(summary_result).strip()

        if not summary and not key_points:
            return "", [], sentiment_breakdown

        sentiment_context = self._build_sentiment_context(sentiment_breakdown)
        context_message = "\n\n".join(
            [
                artifact["context_message"],
                f"SENTIMENT SIGNALS:\n{sentiment_context}",
            ]
        )
        
        try:
            future = self._executor.submit(
                self._run_json_chain,
                system_message="You refine board meeting summaries using transcript context and internal sentiment signals.",
                context_message=context_message,
                user_message="Produce a concise factual summary and key points.",
                response_schema={
                    "summary": "string",
                    "key_points": ["string"],
                },
            )
            payload = future.result(timeout=self._llm_timeout)
        except FutureTimeoutError:
            logger.warning("Summary refinement timed out after %ss", self._llm_timeout)
            payload = {}
        except Exception as exc:
            logger.error("Error in summary refinement: %s", exc)
            payload = {}

        improved_summary = self._extract_text(payload, ("summary",))
        improved_points = self._extract_list(payload, "key_points")

        if improved_summary:
            summary = improved_summary
        if improved_points:
            key_points = improved_points

        return summary, key_points, sentiment_breakdown

    def _run_json_chain(
        self,
        system_message: str,
        context_message: str,
        user_message: Optional[str],
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        schema_hint = self._format_schema_hint(response_schema)
        user_payload = user_message if user_message is not None else ""

        if self._use_langchain:
            raw_text = self._invoke_langchain(
                system_message=system_message,
                context_message=context_message,
                user_message=user_payload,
                schema_hint=schema_hint,
            )
            parsed = self._parse_json(raw_text)
            if parsed is not None:
                return parsed

        fallback_prompt = self._compose_fallback_prompt(
            context_message=context_message,
            user_message=user_payload,
            schema_hint=schema_hint,
        )
        payload = call_llm(fallback_prompt, system_message)

        if isinstance(payload, dict):
            if payload.get("error") and isinstance(payload.get("raw_output"), str):
                parsed_error_payload = self._parse_json(payload.get("raw_output"))
                if parsed_error_payload is not None:
                    return parsed_error_payload
            return payload

        parsed = self._parse_json(payload)
        if parsed is not None:
            return parsed

        return {}

    def _invoke_langchain(
        self,
        system_message: str,
        context_message: str,
        user_message: str,
        schema_hint: str,
    ) -> Optional[str]:
        try:
            from langchain_community.llms import Ollama
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import ChatPromptTemplate
        except Exception:
            return None

        def _invoke():
            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", "{system_message}"),
                    ("human", "CONTEXT MESSAGE:\n{context_message}"),
                    ("human", "USER MESSAGE:\n{user_message}"),
                    ("human", "RESPONSE FORMAT:\n{schema_hint}"),
                ]
            )
            llm = Ollama(
                model=getattr(config, "LLM_MODEL", "llama3"),
                base_url=getattr(config, "OLLAMA_BASE_URL", "http://localhost:11434"),
                timeout=self._llm_timeout,
            )
            chain = prompt_template | llm | StrOutputParser()
            response = chain.invoke(
                {
                    "system_message": system_message,
                    "context_message": context_message,
                    "user_message": user_message,
                    "schema_hint": schema_hint,
                }
            )
            return str(response or "").strip() or None

        try:
            future = self._executor.submit(_invoke)
            return future.result(timeout=self._llm_timeout)
        except FutureTimeoutError:
            logger.warning("LangChain invocation timed out after %ss", self._llm_timeout)
            return None
        except Exception as exc:
            logger.warning("LangChain invocation failed: %s", exc)
            return None

    def _compose_fallback_prompt(self, context_message: str, user_message: str, schema_hint: str) -> str:
        return "\n\n".join(
            [
                f"CONTEXT MESSAGE:\n{context_message}",
                f"USER MESSAGE:\n{user_message}",
                f"RESPONSE FORMAT:\n{schema_hint}",
                "Return ONLY valid JSON.",
            ]
        )

    def _format_schema_hint(self, response_schema: Optional[Dict[str, Any]]) -> str:
        if not response_schema:
            return '{"answer":"string"}'
        return json.dumps(response_schema, ensure_ascii=True)

    def _get_transcript_artifact(
        self,
        meeting_id: str,
        chunks: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        chunk_count = len(chunks)
        cached = self._transcript_cache.get(meeting_id)
        if cached and cached.get("chunk_count") == chunk_count:
            return cached

        transcript_lines: List[str] = []
        speakers = sorted(
            {
                str(chunk.get("speaker", "Unknown")).strip() or "Unknown"
                for chunk in chunks
            }
        )

        for chunk in chunks:
            speaker = str(chunk.get("speaker", "Unknown")).strip() or "Unknown"
            text = str(chunk.get("text", "")).strip()
            if not text:
                continue
            timestamp = chunk.get("timestamp")
            if timestamp is None or timestamp == "":
                transcript_lines.append(f"{speaker}: {text}")
            else:
                transcript_lines.append(f"[{timestamp}s] {speaker}: {text}")

        transcript_text = "\n".join(transcript_lines).strip()
        if not transcript_text:
            if metadata and metadata.get("status") == "no_audio":
                transcript_text = "No audio was detected in this meeting."
            else:
                transcript_text = "No transcript data available yet."

        metadata_payload: Dict[str, Any] = {
            "meeting_id": meeting_id,
            "chunk_count": chunk_count,
            "speaker_count": len(speakers),
            "speakers": speakers,
        }
        if metadata:
            metadata_payload.update(metadata)

        artifact = {
            "meeting_id": meeting_id,
            "chunk_count": chunk_count,
            "speakers": speakers,
            "transcript_text": transcript_text,
            "context_message": self._build_context_message(metadata_payload, transcript_text),
        }
        self._transcript_cache[meeting_id] = artifact
        return artifact

    def _build_context_message(self, metadata: Dict[str, Any], transcript_text: str) -> str:
        metadata_json = json.dumps(metadata, default=str, ensure_ascii=True)
        return "\n\n".join(
            [
                f"MEETING METADATA:\n{metadata_json}",
                f"FULL TRANSCRIPT:\n{transcript_text}",
            ]
        )

    def _build_sentiment_context(self, sentiment_breakdown: Dict[str, Any]) -> str:
        if not sentiment_breakdown:
            return "No sentiment signals available."

        lines = []
        for speaker, data in sentiment_breakdown.items():
            overall = float(data.get("overall_score", 0.0))
            positive = int(data.get("positive_count", 0))
            neutral = int(data.get("neutral_count", 0))
            negative = int(data.get("negative_count", 0))
            dominant = str(data.get("dominant_emotion", "neutral"))
            lines.append(
                f"{speaker}: score={overall:.2f}, positive={positive}, neutral={neutral}, negative={negative}, dominant_emotion={dominant}"
            )
        return "\n".join(lines)

    def _select_relevant_chunks(self, chunks: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        matches = query_by_topic(chunks, query)
        if matches:
            return matches[:25]
        return chunks[:25]

    def _parse_json(self, raw_value: Any) -> Optional[Dict[str, Any]]:
        if isinstance(raw_value, dict):
            return raw_value
        if not isinstance(raw_value, str):
            return None

        text = raw_value.strip()
        if not text:
            return None

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None

        return None

    def _extract_text(self, payload: Dict[str, Any], keys: Tuple[str, ...]) -> str:
        if not isinstance(payload, dict):
            return ""

        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        raw_output = payload.get("raw_output")
        if isinstance(raw_output, str) and raw_output.strip():
            return raw_output.strip()

        return ""

    def _extract_list(self, payload: Dict[str, Any], key: str) -> List[str]:
        if not isinstance(payload, dict):
            return []

        raw_list = payload.get(key)
        if not isinstance(raw_list, list):
            return []

        return [str(item).strip() for item in raw_list if str(item).strip()]

    def _emit_n8n_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        if not self._n8n_webhook_url:
            return

        body = json.dumps({"event": event_name, "payload": payload}).encode("utf-8")
        req = request.Request(
            self._n8n_webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self._n8n_timeout) as response:
                status = getattr(response, "status", 200)
                if status >= 400:
                    logger.warning("n8n webhook returned status %s", status)
        except (error.URLError, TimeoutError, ValueError) as exc:
            logger.warning("Unable to notify n8n webhook: %s", exc)


_meeting_orchestrator = MeetingOrchestrator()


def get_meeting_orchestrator() -> MeetingOrchestrator:
    return _meeting_orchestrator
