"""LLM access for SHERPA.

Groq is the primary provider in both environments. Ollama is a local development fallback and
is unreachable from Streamlit Cloud. The language model is used only for understanding input
and for drafting narrative; it never decides safety-relevant equipment or risk.
"""

from __future__ import annotations

import requests

from .config import get_settings


def complete(
    prompt: str, system: str = "", max_tokens: int = 600, temperature: float = 0.3
) -> str:
    """Return a completion, trying Groq first and falling back to the smaller Groq model,
    then to Ollama when running locally."""
    s = get_settings()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for model in (s.groq_model_primary, s.groq_model_fallback):
        if not s.groq_api_key:
            break
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {s.groq_api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue

    # Local fallback (development only)
    try:
        r = requests.post(
            f"{s.ollama_host}/api/chat",
            json={
                "model": s.ollama_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        return f"(LLM unavailable: {exc})"
