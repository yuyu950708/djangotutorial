"""
AI chat provider helpers for the site.

Currently supports:
- NVIDIA Integrate (OpenAI-style Chat Completions)
- Google Gemini (generateContent; supports optional inline image)
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote

from django.conf import settings

MAX_HISTORY_TURNS = 20
MAX_MESSAGE_CHARS = 4000

# ----- System prompt -----
SYSTEM_PROMPT = """你是「吃什麼」網站的 AI 飲食助理。
規則：
- 一律用繁體中文回答。
- 回答要具體、可執行；必要時可用 Markdown（標題、條列、表格）。
- 使用者如果提到食材、預算、時間、份量、飲食限制，請優先給出符合限制的建議。
- 若資訊不足，先用 1–3 個問題釐清，再給建議。
"""


def _demo_reply(message: str, image) -> str:
    if image:
        return (
            "目前尚未設定任何 AI API Key，所以我只能回覆示範訊息。\n\n"
            "你有上傳圖片，但未設定可用的多模態模型（例如 Gemini）。\n"
            "請在 `.env` 內設定 `GEMINI_API_KEY`（以及可選的 `GEMINI_MODEL`），"
            "然後重啟 Django 伺服器。"
        )
    if message:
        return (
            "目前尚未設定任何 AI API Key，所以我只能回覆示範訊息。\n\n"
            f"你剛剛說：{message}\n\n"
            "請在 `.env` 內設定 `NVIDIA_API_KEY` 或 `GEMINI_API_KEY`，"
            "然後重啟 Django 伺服器。"
        )
    return "目前尚未設定任何 AI API Key，所以我只能回覆示範訊息。"


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
DEFAULT_NVIDIA_MODEL = "meta/llama-3.2-11b-vision-instruct" # "qwen/qwen3.5-397b-a17b" #第一版


def _nvidia_key_from_env() -> str:
    # Back-compat with main.py using `api_key`
    return (os.environ.get("NVIDIA_API_KEY") or os.environ.get("api_key") or "").strip()


def _build_nvidia_messages(
    history: list[dict[str, str]],
    message: str,
    image,
) -> list[dict[str, Any]]:
    """
    Build OpenAI-compatible messages for NVIDIA Integrate.

    For multimodal input, the *user* message content is sent as an array of
    typed content parts: text + image_url(data URL).
    """
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})

    text = (message or "").strip()[:MAX_MESSAGE_CHARS]
    if image:
        raw = image.read()
        image.seek(0)
        b64 = base64.b64encode(raw).decode("ascii")
        mime = getattr(image, "content_type", None) or "image/jpeg"
        if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            mime = "image/jpeg"
        data_url = f"data:{mime};base64,{b64}"
        content: list[dict[str, Any]] = []
        if text:
            content.append({"type": "text", "text": text})
        else:
            content.append({"type": "text", "text": "請描述這張圖片，並給我飲食建議。"})
        content.append({"type": "image_url", "image_url": {"url": data_url}})
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
    temperature: float = 0.7,
    top_p: float = 0.95,
    max_tokens: int = 1024,
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

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        choices = data.get("choices") or []
        if not choices:
            return "NVIDIA API 沒有回傳 choices，請稍後再試。"
        msg = (choices[0].get("message") or {}).get("content") or ""
        msg = msg.strip()
        return msg or "NVIDIA API 回覆為空，請稍後再試。"
    except TimeoutError:
        return (
            "NVIDIA API 讀取回覆逾時（timeout）。\n"
            "建議：稍後再試、降低回覆長度（`max_tokens`）、或換一個模型。"
        )
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
        except Exception:
            raw = ""
        lower = raw.lower()
        if exc.code == 401 or exc.code == 403:
            return "NVIDIA API 權限不足：請確認 `NVIDIA_API_KEY` 正確且仍有效。"
        if exc.code == 429:
            return "NVIDIA API 請求太頻繁（429）：請稍後再試。"
        if exc.code == 400 and raw:
            # Common cases when sending images to a text-only model / unsupported input schema
            if "image" in lower or "multimodal" in lower or "vision" in lower:
                return (
                    "NVIDIA API 回覆 400：看起來你選的模型/設定不支援圖片輸入。\n"
                    "請改用支援 vision 的模型（例如 `meta/llama-3.2-11b-vision-instruct`），"
                    "或在 `.env` 設定 `NVIDIA_MODEL` 後重啟伺服器。"
                )
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
        text_part = (message or "請描述這張圖片，並給出飲食建議。").strip()[:MAX_MESSAGE_CHARS]
        parts: list[dict[str, Any]] = [
            {"text": text_part},
            {"inline_data": {"mime_type": mime, "data": b64}},
        ]
    else:
        parts = [{"text": (message or "你好").strip()[:MAX_MESSAGE_CHARS]}]

    contents.append({"role": "user", "parts": parts})
    return contents


def call_gemini_generate(
    contents: list[dict[str, Any]], *, model: str, api_key: str
) -> str:
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
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        },
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
        return (
            "Gemini API 讀取回覆逾時（timeout）。\n"
            "建議：稍後再試、縮短問題、或改用較快的模型（例如 `gemini-2.0-flash`）。"
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 401 or exc.code == 403:
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


def get_assistant_reply(
    *,
    message: str,
    image,
    history: list[Any],
) -> str:
    hist = _normalize_history(history)

    gemini_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    gemini_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")

    nvidia_key = (getattr(settings, "NVIDIA_API_KEY", "") or "").strip() or _nvidia_key_from_env()
    nvidia_model = getattr(settings, "NVIDIA_MODEL", DEFAULT_NVIDIA_MODEL)
    nvidia_url = getattr(settings, "NVIDIA_INVOKE_URL", DEFAULT_NVIDIA_INVOKE_URL)

    # NVIDIA (supports multimodal via OpenAI-style content parts)
    if nvidia_key:
        msgs = _build_nvidia_messages(hist, message, image)
        return call_nvidia_chat_completions(
            messages=msgs, api_key=nvidia_key, model=nvidia_model, invoke_url=nvidia_url
        )

    # Prefer Gemini when NVIDIA isn't configured
    if gemini_key:
        contents = _build_gemini_contents(hist, message, image)
        return call_gemini_generate(contents, model=gemini_model, api_key=gemini_key)

    return _demo_reply(message, image)
