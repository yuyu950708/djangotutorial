"""
等等吃啥 · AI 美食助理（僅 Google Gemini）。
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote

from django.conf import settings

MAX_HISTORY_TURNS = 20

GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SYSTEM_PROMPT = """你是「等等吃啥」網站的 AI 美食助理。
規則：
- 使用繁體中文，語氣親切、簡潔。
- 以美食、餐廳、聚餐、食譜、營養與飲食建議為主；若離題請簡短帶回美食話題。
- 若使用者上傳食物照片，請描述可見內容並給實用建議（口味、搭配、注意事項）。
- 回覆避免過長；不需要 Markdown 標題層級，條列即可。"""


# ----- 示範模式 -----
def _demo_reply(message: str, image) -> str:
    parts = []
    if message:
        parts.append(
            "（示範模式：請在 .env 設定 GEMINI_API_KEY）\n\n你說：「"
            + message
            + "」"
        )
    else:
        parts.append(
            "（示範模式：請在 .env 設定 GEMINI_API_KEY）\n\n已收到你上傳的圖片。"
        )
    if image:
        parts.append("設定 Google AI 金鑰後，即可辨識餐點並回覆。")
    return "\n".join(parts)


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
        out.append({"role": role, "content": content[:4000]})
    return out


# ----- Google Gemini -----
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
        text_part = (message or "請根據這張圖片給我美食相關建議。").strip()[:4000]
        parts: list[dict[str, Any]] = [
            {"text": text_part},
            {"inline_data": {"mime_type": mime, "data": b64}},
        ]
    else:
        parts = [{"text": (message or "你好").strip()[:4000]}]

    contents.append({"role": "user", "parts": parts})
    return contents


def _parse_google_api_error(exc: urllib.error.HTTPError) -> tuple[str, dict | None]:
    try:
        raw = exc.read().decode("utf-8")
        data = json.loads(raw)
        err = data.get("error", {})
        if isinstance(err, dict):
            return (err.get("message") or raw)[:800], err
        return raw[:800], None
    except Exception:
        return str(exc), None


def _friendly_gemini_message(
    exc: urllib.error.HTTPError, api_message: str, err: dict | None
) -> str:
    status = (err or {}).get("status", "") if err else ""
    lower = (api_message or "").lower()

    if exc.code == 429 or status == "RESOURCE_EXHAUSTED":
        return (
            "Gemini API 額度已用完或請求過於頻繁。\n\n"
            "請到 Google AI Studio 檢查配額與金鑰：\n"
            "https://aistudio.google.com/app/apikey"
        )

    if exc.code in (401, 403) or status == "PERMISSION_DENIED":
        return (
            "Gemini API 金鑰無效或沒有權限。請確認 .env 的 GEMINI_API_KEY 正確，"
            "並在 Google AI Studio 啟用 Generative Language API。"
        )

    if exc.code == 404:
        return (
            "找不到指定的 Gemini 模型（名稱錯誤或此帳戶尚未開放）。\n"
            "請在 .env 調整 GEMINI_MODEL，例如 gemini-2.0-flash 或 gemini-1.5-flash，"
            "存檔後重新啟動 runserver。"
        )

    if exc.code == 400:
        if "api key" in lower or "api_key" in lower:
            return (
                "Gemini 未收到有效金鑰。\n"
                "請確認專案根目錄的 .env 有 GEMINI_API_KEY（勿加引號），存檔後重新啟動 "
                "runserver；金鑰請到 https://aistudio.google.com/app/apikey 建立或更換。"
            )
        return f"請求被拒絕：{api_message[:400]}"

    return f"Gemini API 錯誤 [{exc.code}]：{api_message[:400]}"


def call_gemini_generate(
    contents: list[dict[str, Any]], *, model: str, api_key: str
) -> str:
    key = (api_key or "").strip()
    if not key:
        return (
            "（未設定 GEMINI_API_KEY。請在專案根目錄 .env 設定後重新啟動伺服器。）"
        )

    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024},
    }
    # Google AI Studio 金鑰：REST 可用 ?key= 與 x-goog-api-key（兩者併用相容性較佳）
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
            return "（Gemini 未產生回覆，可能被安全設定擋下，請換個說法或圖片再試。）"
        cand = candidates[0]
        content = cand.get("content") or {}
        parts = content.get("parts") or []
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        out = "\n".join(t for t in texts if t).strip()
        if out:
            return out
        reason = cand.get("finishReason", "")
        return f"（Gemini 結束原因：{reason or '無文字'}，請換個方式提問。）"
    except urllib.error.HTTPError as exc:
        api_message, err_obj = _parse_google_api_error(exc)
        friendly = _friendly_gemini_message(exc, api_message, err_obj)
        return f"（{friendly}）"
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, IndexError) as exc:
        return f"（Gemini 連線失敗：{exc}）"


def get_assistant_reply(
    *,
    message: str,
    image,
    history: list[Any],
) -> str:
    gemini_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    gemini_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")

    hist = _normalize_history(history)

    if gemini_key:
        contents = _build_gemini_contents(hist, message, image)
        return call_gemini_generate(contents, model=gemini_model, api_key=gemini_key)

    return _demo_reply(message, image)
