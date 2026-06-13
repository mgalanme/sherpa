#!/usr/bin/env python3
"""smoke_llm.py - Verifies the Groq API (primary, both environments) and, if present, the
local Ollama model (development fallback). Reads GROQ_API_KEY, GROQ_MODEL_PRIMARY,
OLLAMA_HOST and OLLAMA_MODEL from the environment. Run inside .venv-langchain.
"""

import os
import sys

import requests

ok = True

groq_key = os.environ.get("GROQ_API_KEY", "")
groq_model = os.environ.get("GROQ_MODEL_PRIMARY", "llama-3.3-70b-versatile")
if groq_key:
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}"},
            json={
                "model": groq_model,
                "max_tokens": 8,
                "messages": [
                    {"role": "user", "content": "Reply with the single word: ready"}
                ],
            },
            timeout=30,
        )
        r.raise_for_status()
        print(f"  [ OK ] Groq reachable; model {groq_model} responded.")
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] Groq check failed: {exc}")
        ok = False
else:
    print("  [WARN] GROQ_API_KEY not set; skipping Groq check.")
    ok = False

host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
model = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
try:
    r = requests.get(f"{host}/api/tags", timeout=10)
    r.raise_for_status()
    tags = [m.get("name", "") for m in r.json().get("models", [])]
    present = any(model.split(":")[0] in t for t in tags)
    print(
        f"  [ OK ] Ollama reachable at {host}; {model} {'present' if present else 'NOT pulled yet'}"
    )
except Exception:
    print(
        f"  [INFO] Ollama not reachable at {host} (expected if running in the cloud)."
    )

sys.exit(0 if ok else 1)
