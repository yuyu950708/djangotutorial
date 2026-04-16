"""
Local CLI test script for NVIDIA Integrate Chat Completions.

This file is NOT used by Django at runtime; the web chatbot lives in `posts/ai_chat.py`.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

INVOKE_URL = os.environ.get(
    "NVIDIA_INVOKE_URL", "https://integrate.api.nvidia.com/v1/chat/completions"
).strip()
API_KEY = (os.environ.get("NVIDIA_API_KEY") or os.environ.get("api_key") or "").strip()
MODEL = os.environ.get("NVIDIA_MODEL", "qwen/qwen3.5-397b-a17b").strip()

SYSTEM_PROMPT = """你是一個有幫助的 AI 助理。
請用繁體中文回答，必要時可用 Markdown 條列說明。
"""


def chat_once(user_text: str) -> str:
    if not API_KEY:
        return "缺少 NVIDIA API Key：請在 `.env` 設定 `NVIDIA_API_KEY`（或 `api_key`）。"

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": 1024,
        "temperature": 0.7,
        "top_p": 0.95,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        INVOKE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
    except TimeoutError:
        return "讀取回覆逾時（timeout）。請稍後再試，或降低 `max_tokens` / 換模型。"
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
        except Exception:
            raw = ""
        if raw:
            return f"HTTP {exc.code}: {raw[:500]}"
        return f"HTTP {exc.code}: {exc}"
    except Exception as exc:
        return f"Error: {exc}"


def main() -> int:
    user_text = input("你想問什麼？ ").strip()
    if not user_text:
        return 0
    print("\n--- AI 回覆 ---\n")
    print(chat_once(user_text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

