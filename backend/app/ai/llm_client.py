import subprocess
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def call_llm(prompt: str, system: str = "", timeout: float = 30.0) -> dict:
    """
    Calls Ollama LLaMA 3 locally with timeout protection.
    Always tries to return JSON.
    
    Args:
        prompt: User prompt
        system: System message
        timeout: Maximum execution time in seconds
        
    Returns:
        Dict with result or error
    """
    full_prompt = f"""
{system}

USER INPUT:
{prompt}

INSTRUCTIONS:
- Respond in STRICT JSON
- Do not add explanations
- Do not add markdown
"""

    try:
        process = subprocess.run(
            ["ollama", "run", "llama3"],
            input=full_prompt,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        
        output = process.stdout.strip()
        
        if process.returncode != 0:
            logger.error("LLM process failed: %s", process.stderr)
            return {
                "error": "LLM process failed",
                "raw_output": output or process.stderr
            }

        # Attempt JSON parsing
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {
                "error": "Invalid JSON from LLM",
                "raw_output": output
            }
            
    except subprocess.TimeoutExpired:
        logger.error("LLM call timed out after %s seconds", timeout)
        return {
            "error": f"LLM timeout after {timeout}s",
            "raw_output": ""
        }
    except FileNotFoundError:
        logger.error("Ollama not found - is it installed?")
        return {
            "error": "Ollama not found",
            "raw_output": ""
        }
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return {
            "error": str(exc),
            "raw_output": ""
        }
