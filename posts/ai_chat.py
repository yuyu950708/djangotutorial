"""
AI chat provider helpers for the site.

Providers:
- NVIDIA Integrate (OpenAI-compatible /v1/chat/completions; supports vision models)
- Google Gemini (generateContent; supports optional inline image)
"""

from __future__ import annotations

import base64
import binascii
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
- 回答請務必簡明扼要，除非使用者要求，否則請保持在 150 字以內。
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


# 前端解碼後、以及 multipart 上傳時允許的 MIME（與 views 驗證一致）
_ALLOWED_IMAGE_MIMES = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})


def decode_client_image_base64(image_base64: str | None) -> tuple[str, bytes] | None:
    """
    將前端 `FileReader.readAsDataURL` 或純 Base64 字串還原成 (mime, 原始位元組)。

    - Data URL：`data:image/png;base64,XXXX` → 會去掉 `data:` 與 `;base64,` 前綴，只把 XXXX 解碼。
    - 純 base64：MIME 預設為 image/jpeg（建議前端仍傳 Data URL 以便辨識格式）。
    - 若欄位為空字串 / None → 回傳 None（表示本則訊息沒有附圖）。
    - 若偵測到 blob: 或 http(s):（常見誤傳「路徑」）→ 拋 ValueError。
    """
    if image_base64 is None or not isinstance(image_base64, str):
        return None
    s = image_base64.strip()
    if not s:
        return None

    lowered = s.lower()
    if lowered.startswith("blob:") or lowered.startswith("http://") or lowered.startswith("https://"):
        raise ValueError("圖片必須以 Base64 傳送，請勿使用 blob 或網址路徑。")

    mime = "image/jpeg"
    if s.startswith("data:"):
        # 格式：data:[<mediatype>][;parameters];base64,<data>
        try:
            header, b64_payload = s.split(",", 1)
        except ValueError as exc:
            raise ValueError("圖片 Data URL 格式無效。") from exc
        if ";base64" not in header.lower():
            raise ValueError("圖片必須為 base64 的 Data URL（需含 ;base64,）。")
        semi = header.find(";")
        if semi > 5:
            candidate = header[5:semi].strip().lower()
            if candidate:
                mime = candidate
        b64_str = "".join(b64_payload.split())
    else:
        # 純 base64（無 data: 前綴）
        b64_str = "".join(s.split())

    try:
        raw = base64.b64decode(b64_str, validate=True)
    except (binascii.Error, ValueError):
        pad = (-len(b64_str)) % 4
        try:
            raw = base64.b64decode(b64_str + ("=" * pad), validate=False)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("圖片 Base64 解碼失敗，請確認檔案是否完整。") from exc

    if not raw:
        raise ValueError("解碼後的圖片內容為空。")
    if mime not in _ALLOWED_IMAGE_MIMES:
        raise ValueError("不支援的圖片格式，請使用 JPG、PNG、GIF 或 WebP。")
    return (mime, raw)


# =========================
# NVIDIA Integrate (OpenAI-style)
# =========================

DEFAULT_NVIDIA_INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
# Use a vision-capable model by default so image uploads work out-of-the-box.
DEFAULT_NVIDIA_MODEL = "meta/llama-3.2-11b-vision-instruct"


class AIProviderError(Exception):
    def __init__(self, message: str, *, transient: bool = False):
        super().__init__(message)
        self.message = message
        self.transient = transient


def _nvidia_key_from_env() -> str:
    return (os.environ.get("NVIDIA_API_KEY") or os.environ.get("api_key") or "").strip()


def _nvidia_compress_to_jpeg_b64(raw: bytes, *, mime_hint: str | None) -> tuple[str, str]:
    """
    將圖片位元組壓成較小的 JPEG base64（無 data: 前綴），降低 NVIDIA gateway 502 風險。
    回傳 (mime, base64字串)。
    """
    target_bytes = 120 * 1024  # base64 膨脹約 33%，控制 JSON 體積

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
        mime = (mime_hint or "image/jpeg").lower()
        if mime not in _ALLOWED_IMAGE_MIMES:
            mime = "image/jpeg"
        b64 = base64.b64encode(raw).decode("ascii")
        return (mime, b64)


def _build_nvidia_messages(
    history: list[dict[str, str]],
    message: str,
    image: tuple[str, bytes] | None,
) -> list[dict[str, Any]]:
    """
    組 NVIDIA / OpenAI 相容的 chat/completions 訊息。

    有圖片時使用官方視覺格式（多段 content）：
    - 文字：`{"type":"text","text":"..."}`
    - 圖片：`{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}`
    勿再嵌入 HTML `<img>`，避免模型只當成無效字串。
    """
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})

    text = (message or "").strip()[:MAX_MESSAGE_CHARS]
    if image:
        mime_hint, raw_bytes = image
        mime, b64 = _nvidia_compress_to_jpeg_b64(raw_bytes, mime_hint=mime_hint)
        prompt = text or "請描述這張圖片，並估算大概熱量（若不確定請說明理由與假設）。"
        # OpenAI Vision / NVIDIA 相容：data URL 放在 image_url.url
        content: list[dict[str, Any]] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]
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
    max_tokens: int = 200,
) -> str:
    key = (api_key or "").strip()
    if not key:
        raise AIProviderError(
            "缺少 NVIDIA API Key：請在 `.env` 設定 `NVIDIA_API_KEY`（或 `api_key`）。",
            transient=False,
        )

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
        with urllib.request.urlopen(req, timeout=max(10, int(getattr(settings, "AI_REQUEST_TIMEOUT_SECONDS", 60)))) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        data = _do()
        choices = data.get("choices") or []
        if not choices:
            raise AIProviderError("NVIDIA API 沒有回傳 choices，請稍後再試。", transient=True)
        msg = (choices[0].get("message") or {}).get("content") or ""
        msg = (msg or "").strip()
        if not msg:
            raise AIProviderError("NVIDIA API 回覆為空，請稍後再試。", transient=True)
        return msg
    except TimeoutError:
        raise AIProviderError("NVIDIA API 讀取回覆逾時（timeout），請稍後再試。", transient=True)
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
            raise AIProviderError(
                f"NVIDIA API 上游暫時性錯誤（HTTP {exc.code}）。\n"
                "請稍後重試；如果你是傳圖片，建議換更小/更清晰的圖片（避免超高解析），"
                "或改用 Gemini（較穩定）。"
                ,
                transient=True,
            )

        if exc.code in (401, 403):
            raise AIProviderError("NVIDIA API 權限不足：請確認 `NVIDIA_API_KEY` 正確且仍有效。", transient=False)
        if exc.code == 429:
            raise AIProviderError("NVIDIA API 請求太頻繁（429）：請稍後再試。", transient=True)

        if raw:
            raise AIProviderError(f"NVIDIA API 錯誤（HTTP {exc.code}）：{raw[:500]}", transient=True)
        raise AIProviderError(f"NVIDIA API 錯誤（HTTP {exc.code}）：{exc}", transient=True)
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as exc:
        raise AIProviderError(f"NVIDIA API 連線/解析失敗：{exc}", transient=True)


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
    image: tuple[str, bytes] | None,
) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for h in history:
        gr = _gemini_role(h["role"])
        if not gr:
            continue
        contents.append({"role": gr, "parts": [{"text": h["content"]}]})

    if image:
        mime, raw = image
        # Gemini REST：inlineData.mimeType + data；data 僅為純 base64，不含 data:image/... 前綴
        b64 = base64.b64encode(raw).decode("ascii")
        text_part = (message or "請描述這張圖片並給出飲食建議。").strip()[:MAX_MESSAGE_CHARS]
        parts: list[dict[str, Any]] = [
            {"text": text_part},
            {"inlineData": {"mimeType": mime, "data": b64}},
        ]
    else:
        parts = [{"text": (message or "你好").strip()[:MAX_MESSAGE_CHARS]}]

    contents.append({"role": "user", "parts": parts})
    return contents


def call_gemini_generate(contents: list[dict[str, Any]], *, model: str, api_key: str) -> str:
    key = (api_key or "").strip()
    if not key:
        raise AIProviderError("缺少 Gemini API Key：請在 `.env` 設定 `GEMINI_API_KEY`。", transient=False)

    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 200},
    }
    url = GEMINI_GENERATE_URL.format(model=model) + f"?key={quote(key, safe='')}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=max(10, int(getattr(settings, "AI_REQUEST_TIMEOUT_SECONDS", 60)))) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        candidates = data.get("candidates") or []
        if not candidates:
            raise AIProviderError("Gemini 沒有回傳候選回覆，請稍後再試。", transient=True)
        cand = candidates[0]
        content = cand.get("content") or {}
        parts = content.get("parts") or []
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        out = "\n".join(t for t in texts if t).strip()
        if not out:
            raise AIProviderError("Gemini 回覆為空，請稍後再試。", transient=True)
        return out
    except TimeoutError:
        raise AIProviderError("Gemini API 讀取回覆逾時（timeout），請稍後再試。", transient=True)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise AIProviderError("Gemini API 權限不足：請確認 `GEMINI_API_KEY` 正確且已開啟 API。", transient=False)
        if exc.code == 429:
            raise AIProviderError("Gemini API 請求太頻繁（429）：請稍後再試。", transient=True)
        try:
            raw = exc.read().decode("utf-8")
        except Exception:
            raw = ""
        if raw:
            raise AIProviderError(f"Gemini API 錯誤（HTTP {exc.code}）：{raw[:500]}", transient=True)
        raise AIProviderError(f"Gemini API 錯誤（HTTP {exc.code}）：{exc}", transient=True)
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as exc:
        raise AIProviderError(f"Gemini API 連線/解析失敗：{exc}", transient=True)


# =========================
# Entry point used by the view
# =========================


def get_assistant_reply(
    *,
    message: str,
    image: tuple[str, bytes] | None,
    history: list[Any],
) -> tuple[str, str]:
    """
    image: 已由 view 解出之 (mime_type, raw_bytes)；無圖則為 None。
    """
    hist = _normalize_history(history)

    nvidia_key = (getattr(settings, "NVIDIA_API_KEY", "") or "").strip() or _nvidia_key_from_env()
    nvidia_model = getattr(settings, "NVIDIA_MODEL", DEFAULT_NVIDIA_MODEL)
    nvidia_backup_key = (getattr(settings, "NVIDIA_BACKUP_API_KEY", "") or "").strip()
    nvidia_backup_model = getattr(settings, "NVIDIA_BACKUP_MODEL", nvidia_model)
    nvidia_url = getattr(settings, "NVIDIA_INVOKE_URL", DEFAULT_NVIDIA_INVOKE_URL)

    gemini_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    gemini_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")

    # Prefer NVIDIA primary -> NVIDIA backup -> Gemini.
    msgs = _build_nvidia_messages(hist, message, image)
    nvidia_errors: list[str] = []
    if nvidia_key:
        try:
            reply = call_nvidia_chat_completions(
                messages=msgs, api_key=nvidia_key, model=nvidia_model, invoke_url=nvidia_url
            )
            return reply, nvidia_model
        except AIProviderError as exc:
            nvidia_errors.append(f"主模型失敗：{exc.message}")

    if nvidia_backup_key and nvidia_backup_key != nvidia_key:
        try:
            reply = call_nvidia_chat_completions(
                messages=msgs, api_key=nvidia_backup_key, model=nvidia_backup_model, invoke_url=nvidia_url
            )
            return reply, nvidia_backup_model
        except AIProviderError as exc:
            nvidia_errors.append(f"備援模型失敗：{exc.message}")

    if gemini_key:
        contents = _build_gemini_contents(hist, message, image)
        try:
            reply = call_gemini_generate(contents, model=gemini_model, api_key=gemini_key)
            return reply, gemini_model
        except AIProviderError as exc:
            if nvidia_errors:
                return f"{'; '.join(nvidia_errors)}；Gemini 也失敗：{exc.message}", "fallback-error"
            return exc.message, "gemini-error"

    if nvidia_errors:
        return "；".join(nvidia_errors), "nvidia-error"

    return _demo_reply(message, bool(image)), "demo"

