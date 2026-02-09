import subprocess
import json

def call_llm(prompt: str, system: str = "") -> dict:
    """
    Calls Ollama LLaMA 3 locally.
    Always tries to return JSON.
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

    process = subprocess.run(
        ["ollama", "run", "llama3"],
        input=full_prompt,
        text=True,
        capture_output=True
    )

    output = process.stdout.strip()

    # Attempt JSON parsing
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {
            "error": "Invalid JSON from LLM",
            "raw_output": output
        }
