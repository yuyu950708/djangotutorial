"""
AI chat provider helpers for the site.

Providers:
- NVIDIA Integrate (OpenAI-compatible /v1/chat/completions; supports vision models)
- Google Gemini (generateContent; supports optional inline image)
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote

from django.conf import settings

MAX_HISTORY_TURNS = 20
MAX_MESSAGE_CHARS = 4000

SYSTEM_PROMPT = """你是「等等吃啥」網站的 AI 美食助理。
規則：
- 一律用繁體中文回答。
- 針對美食、餐廳、聚餐、料理、營養與飲食建議提供具體可執行的回答。
- 如果使用者上傳食物照片：先描述你看到的內容，再估算大概熱量（若不確定要說明假設與不確定性）。
- 資訊不足時先問 1–3 個問題釐清。
"""


def _demo_reply(message: str, image) -> str:
    if image:
        return "尚未設定可用的 AI API Key（NVIDIA_API_KEY 或 GEMINI_API_KEY）。"
    if message:
        return f"（示範模式）你說：{message}\n\n請在 `.env` 設定 NVIDIA_API_KEY 或 GEMINI_API_KEY。"
    return "（示範模式）請輸入訊息。"


def _normalize_history(history: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(history, list):
        return out
    for item in history[-MAX_HISTORY_TURNS:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        out.append({"role": role, "content": content[:MAX_MESSAGE_CHARS]})
    return out


# =========================
# NVIDIA Integrate (OpenAI-style)
# =========================

DEFAULT_NVIDIA_INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
# Use a vision-capable model by default so image uploads work out-of-the-box.
DEFAULT_NVIDIA_MODEL = "meta/llama-3.2-11b-vision-instruct"


def _nvidia_key_from_env() -> str:
    return (os.environ.get("NVIDIA_API_KEY") or os.environ.get("api_key") or "").strip()


def _nvidia_inline_image_data_url(image) -> tuple[str, str]:
    """
    NVIDIA Integrate docs mention large image payloads may require Asset APIs.
    To avoid gateway 5xx (e.g. 502), downscale/compress aggressively.

    Returns (mime, base64).
    """
    raw = image.read()
    image.seek(0)

    target_bytes = 120 * 1024  # base64 overhead ~33%, keep JSON reasonably small

    try:
        from PIL import Image

        im = Image.open(io.BytesIO(raw))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")

        max_side = 768
        w, h = im.size
        if max(w, h) > max_side:
            scale = max_side / max(w, h)
            im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

        quality = 72
        data = b""
        for _ in range(7):
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=quality, optimize=True)
            data = buf.getvalue()
            if len(data) <= target_bytes:
                break
            quality = max(40, quality - 8)
            if quality <= 48:
                w2, h2 = im.size
                im = im.resize((max(1, int(w2 * 0.85)), max(1, int(h2 * 0.85))), Image.LANCZOS)

        b64 = base64.b64encode(data if data else raw).decode("ascii")
        return ("image/jpeg", b64)
    except Exception:
        mime = (getattr(image, "content_type", None) or "image/jpeg").lower()
        if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            mime = "image/jpeg"
        b64 = base64.b64encode(raw).decode("ascii")
        return (mime, b64)


def _build_nvidia_messages(history: list[dict[str, str]], message: str, image) -> list[dict[str, Any]]:
    """
    Build messages for NVIDIA Integrate.

    For images, use string content with an HTML <img src="data:...;base64,..."/> tag.
    This matches NVIDIA Integrate docs for passing base64 images with role=user.
    """
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})

    text = (message or "").strip()[:MAX_MESSAGE_CHARS]
    if image:
        mime, b64 = _nvidia_inline_image_data_url(image)
        prompt = text or "請描述這張圖片，並估算大概熱量（若不確定請說明理由與假設）。"
        content = f'{prompt}\n<img src="data:{mime};base64,{b64}" />'
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": text})

    return messages


def call_nvidia_chat_completions(
    *,
    messages: list[dict[str, Any]],
    api_key: str,
    model: str,
    invoke_url: str = DEFAULT_NVIDIA_INVOKE_URL,
    temperature: float = 0.4,
    top_p: float = 0.95,
    max_tokens: int = 512,
) -> str:
    key = (api_key or "").strip()
    if not key:
        return "缺少 NVIDIA API Key：請在 `.env` 設定 `NVIDIA_API_KEY`（或 `api_key`）。"

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    req = urllib.request.Request(
        invoke_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
        method="POST",
    )

    def _do() -> dict[str, Any]:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        data = _do()
        choices = data.get("choices") or []
        if not choices:
            return "NVIDIA API 沒有回傳 choices，請稍後再試。"
        msg = (choices[0].get("message") or {}).get("content") or ""
        return (msg or "").strip() or "NVIDIA API 回覆為空，請稍後再試。"
    except TimeoutError:
        return "NVIDIA API 讀取回覆逾時（timeout），請稍後再試。"
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
        except Exception:
            raw = ""

        if exc.code in (502, 503, 504):
            # transient gateway / upstream issues; quick single retry
            time.sleep(0.8)
            try:
                data = _do()
                choices = data.get("choices") or []
                if choices:
                    msg = (choices[0].get("message") or {}).get("content") or ""
                    msg = (msg or "").strip()
                    if msg:
                        return msg
            except Exception:
                pass
            return (
                f"NVIDIA API 上游暫時性錯誤（HTTP {exc.code}）。\n"
                "請稍後重試；如果你是傳圖片，建議換更小/更清晰的圖片（避免超高解析），"
                "或改用 Gemini（較穩定）。"
            )

        if exc.code in (401, 403):
            return "NVIDIA API 權限不足：請確認 `NVIDIA_API_KEY` 正確且仍有效。"
        if exc.code == 429:
            return "NVIDIA API 請求太頻繁（429）：請稍後再試。"

        if raw:
            return f"NVIDIA API 錯誤（HTTP {exc.code}）：{raw[:500]}"
        return f"NVIDIA API 錯誤（HTTP {exc.code}）：{exc}"
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as exc:
        return f"NVIDIA API 連線/解析失敗：{exc}"


# =========================
# Google Gemini (generateContent)
# =========================

GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


def _gemini_role(role: str) -> str | None:
    if role == "user":
        return "user"
    if role == "assistant":
        return "model"
    return None


def _build_gemini_contents(
    history: list[dict[str, str]],
    message: str,
    image,
) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for h in history:
        gr = _gemini_role(h["role"])
        if not gr:
            continue
        contents.append({"role": gr, "parts": [{"text": h["content"]}]})

    if image:
        raw = image.read()
        image.seek(0)
        b64 = base64.b64encode(raw).decode("ascii")
        mime = getattr(image, "content_type", None) or "image/jpeg"
        if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            mime = "image/jpeg"
        text_part = (message or "請描述這張圖片並給出飲食建議。").strip()[:MAX_MESSAGE_CHARS]
        parts: list[dict[str, Any]] = [
            {"text": text_part},
            {"inline_data": {"mime_type": mime, "data": b64}},
        ]
    else:
        parts = [{"text": (message or "你好").strip()[:MAX_MESSAGE_CHARS]}]

    contents.append({"role": "user", "parts": parts})
    return contents


def call_gemini_generate(contents: list[dict[str, Any]], *, model: str, api_key: str) -> str:
    key = (api_key or "").strip()
    if not key:
        return "缺少 Gemini API Key：請在 `.env` 設定 `GEMINI_API_KEY`。"

    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024},
    }
    url = GEMINI_GENERATE_URL.format(model=model) + f"?key={quote(key, safe='')}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        candidates = data.get("candidates") or []
        if not candidates:
            return "Gemini 沒有回傳候選回覆，請稍後再試。"
        cand = candidates[0]
        content = cand.get("content") or {}
        parts = content.get("parts") or []
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        out = "\n".join(t for t in texts if t).strip()
        return out or "Gemini 回覆為空，請稍後再試。"
    except TimeoutError:
        return "Gemini API 讀取回覆逾時（timeout），請稍後再試。"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return "Gemini API 權限不足：請確認 `GEMINI_API_KEY` 正確且已開啟 API。"
        if exc.code == 429:
            return "Gemini API 請求太頻繁（429）：請稍後再試。"
        try:
            raw = exc.read().decode("utf-8")
        except Exception:
            raw = ""
        if raw:
            return f"Gemini API 錯誤（HTTP {exc.code}）：{raw[:500]}"
        return f"Gemini API 錯誤（HTTP {exc.code}）：{exc}"
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as exc:
        return f"Gemini API 連線/解析失敗：{exc}"


# =========================
# Entry point used by the view
# =========================


def get_assistant_reply(*, message: str, image, history: list[Any]) -> str:
    hist = _normalize_history(history)

    nvidia_key = (getattr(settings, "NVIDIA_API_KEY", "") or "").strip() or _nvidia_key_from_env()
    nvidia_model = getattr(settings, "NVIDIA_MODEL", DEFAULT_NVIDIA_MODEL)
    nvidia_url = getattr(settings, "NVIDIA_INVOKE_URL", DEFAULT_NVIDIA_INVOKE_URL)

    gemini_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    gemini_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")

    # Prefer NVIDIA if configured (supports images via embedded <img> base64)
    if nvidia_key:
        msgs = _build_nvidia_messages(hist, message, image)
        return call_nvidia_chat_completions(messages=msgs, api_key=nvidia_key, model=nvidia_model, invoke_url=nvidia_url)

    if gemini_key:
        contents = _build_gemini_contents(hist, message, image)
        return call_gemini_generate(contents, model=gemini_model, api_key=gemini_key)

    return _demo_reply(message, image)

