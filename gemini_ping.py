"""
測試 .env 的 GEMINI_API_KEY / GEMINI_MODEL 是否可呼叫 Gemini API。
用法（專案根目錄）：python gemini_ping.py
"""
from __future__ import annotations

import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", encoding="utf-8-sig")
except ImportError:
    print("請安裝 python-dotenv：pip install python-dotenv", file=sys.stderr)
    sys.exit(1)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


def main() -> int:
    key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    model = (os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash").strip()

    if not key:
        print("錯誤：未讀到 GEMINI_API_KEY（請在專案根目錄 .env 設定）")
        return 1

    print(f"模型：{model}")
    print("金鑰：已讀取（長度 {} 字元）".format(len(key)))

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": '請只回覆一個字：好'}],
            }
        ],
        "generationConfig": {"maxOutputTokens": 32},
    }
    url = GEMINI_URL.format(model=model)
    from urllib.parse import quote

    url_with_key = url + f"?key={quote(key, safe='')}"
    req = urllib.request.Request(
        url_with_key,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        print(f"\nHTTP {e.code}")
        try:
            err = json.loads(raw)
            msg = err.get("error", {})
            text = msg.get("message", raw[:800]) if isinstance(msg, dict) else raw[:800]
        except json.JSONDecodeError:
            text = raw[:800]
        print(text)
        if e.code == 429:
            print(
                "\n（金鑰已被 API 接受；若出現 quota / rate limit，"
                "代表配額或免費額度用盡，請稍後再試或到 AI Studio 查看用量。）"
            )
        elif e.code in (401, 403):
            print("\n（金鑰無效或無權限，請檢查 GEMINI_API_KEY。）")
        return 2
    except urllib.error.URLError as e:
        print(f"\n連線失敗：{e}")
        return 3

    parts = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
    reply = "".join(texts).strip()
    print("\n成功。模型回覆摘錄：")
    print(reply[:300] if reply else "(無文字)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
