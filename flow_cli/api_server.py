import argparse
import asyncio
import base64
import json
import re
import secrets
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from .client import ImageGenerator
from .config import get_config
from .models import IMAGE_MODELS, DEFAULT_MODEL
from .personal_captcha import async_playwright


API_KEY_ENV = "FLOW_API_KEY"
DEFAULT_API_KEY = "flow-local-key"
OUTPUT_ROOT = Path(tempfile.gettempdir()) / "flow-image-api"
DEBUG_ROOT = OUTPUT_ROOT / "_debug"
PROFILE_ROOT = Path.home() / ".flow-cli" / "browser-profile"


class ImageGenerationRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL)
    prompt: str
    size: Optional[str] = Field(default=None, description="1024x1024 / 1024x1536 / 1536x1024")
    aspect_ratio: Optional[str] = Field(default=None, description="1:1 / 9:16 / 16:9 / 21:9")
    quality: Optional[str] = Field(default="standard", description="standard / hd / 2k / 4k")
    response_format: Optional[str] = Field(default="url", description="url / b64_json")
    n: int = Field(default=1)


class ChatCompletionRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL)
    messages: list[dict[str, Any]]
    size: Optional[str] = None
    quality: Optional[str] = None
    aspect_ratio: Optional[str] = None
    response_format: Optional[str] = "url"
    stream: Optional[bool] = False
    n: Optional[int] = 1

    model_config = {"extra": "allow"}


class LoginSessionManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._playwright = None
        self._context = None
        self._page = None

    async def open(self, flow_url: str) -> None:
        async with self._lock:
            if self._context is not None:
                if self._page is None:
                    self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
                await self._page.goto(flow_url, wait_until="domcontentloaded", timeout=60000)
                return

            PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
            self._playwright = await async_playwright().start()
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_ROOT),
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-default-browser-check",
                    "--disable-dev-shm-usage",
                ],
                viewport={"width": 1440, "height": 900},
            )
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            await self._page.goto(flow_url, wait_until="domcontentloaded", timeout=60000)

    async def extract_st(self) -> str:
        async with self._lock:
            if self._context is None:
                raise HTTPException(status_code=400, detail="Login browser is not open")
            cookies = await self._context.cookies("https://labs.google/", "https://labs.google/fx/tools/flow")
            for cookie in cookies:
                if cookie.get("name") == "__Secure-next-auth.session-token" and cookie.get("value"):
                    return cookie["value"]
            raise HTTPException(status_code=400, detail="Flow session token not found. Please confirm Google Flow login is complete.")

    async def has_st_cookie(self) -> bool:
        async with self._lock:
            if self._context is None:
                return False
            cookies = await self._context.cookies("https://labs.google/", "https://labs.google/fx/tools/flow")
            return any(cookie.get("name") == "__Secure-next-auth.session-token" and cookie.get("value") for cookie in cookies)

    async def close(self) -> None:
        async with self._lock:
            if self._context is not None:
                await self._context.close()
                self._context = None
                self._page = None
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None

    async def is_open(self) -> bool:
        async with self._lock:
            return self._context is not None


login_manager = LoginSessionManager()


def get_api_key() -> str:
    import os

    return os.environ.get(API_KEY_ENV, DEFAULT_API_KEY)


def verify_api_key(authorization: Optional[str] = Header(default=None)) -> None:
    expected = get_api_key()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    provided = authorization.split(" ", 1)[1].strip()
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")


def build_output_path(tag: str = "image") -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{tag}_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
    return OUTPUT_ROOT / filename


def normalize_quality(quality: Optional[str]) -> str:
    value = (quality or "standard").strip().lower()
    if value in {"hd", "2k"}:
        return "2k"
    if value == "4k":
        return "4k"
    if value in {"1k", "standard", "default", "original"}:
        return "none"
    return "none"


def normalize_size(size: Optional[str]) -> Optional[str]:
    if not size:
        return None
    value = size.strip().lower().replace(" ", "")
    if value in {"1k", "2k", "4k"}:
        return None
    mapping = {
        "1024x1024": "square",
        "1024x1536": "portrait",
        "1536x1024": "landscape",
        "1024x768": "landscape",
        "768x1024": "portrait",
        "2048x2048": "square",
        "2048x3072": "portrait",
        "3072x2048": "landscape",
        "4096x4096": "square",
        "4096x6144": "portrait",
        "6144x4096": "landscape",
    }
    return mapping.get(value)


def normalize_aspect_ratio(aspect_ratio: Optional[str]) -> Optional[str]:
    if not aspect_ratio:
        return None
    value = aspect_ratio.strip().lower().replace(" ", "")
    mapping = {
        "1:1": "square",
        "16:9": "landscape",
        "9:16": "portrait",
        "4:3": "landscape",
        "3:4": "portrait",
        "21:9": "ultrawide",
        "9:21": "portrait",
    }
    return mapping.get(value)


def detect_orientation(size: Optional[str], aspect_ratio: Optional[str]) -> str:
    return normalize_aspect_ratio(aspect_ratio) or normalize_size(size) or "landscape"


def get_model_variants(requested: str) -> Optional[dict[str, str]]:
    normalized = "".join(ch for ch in requested.lower() if ch.isalnum())
    variants = {
        "gemini-3.1-flash-image": {
            "landscape": "gemini-3.1-flash-image-landscape",
            "portrait": "gemini-3.1-flash-image-portrait",
            "square": "gemini-3.1-flash-image-square",
        },
        "gemini-3.0-pro-image": {
            "landscape": "gemini-3.0-pro-image-landscape",
            "portrait": "gemini-3.0-pro-image-portrait",
            "square": "gemini-3.0-pro-image-square",
        },
        "imagen-4.0-generate-preview": {
            "landscape": "imagen-4.0-generate-preview-landscape",
            "portrait": "imagen-4.0-generate-preview-portrait",
            "square": "imagen-4.0-generate-preview-landscape",
        },
        "nano-banana-2": {
            "landscape": "nano-banana-2-landscape",
            "portrait": "nano-banana-2-portrait",
            "square": "nano-banana-2-square",
            "ultrawide": "nano-banana-2-ultrawide",
        },
        "nano-banana-pro": {
            "landscape": "nano-banana-pro-landscape",
            "portrait": "nano-banana-pro-portrait",
            "square": "nano-banana-pro-square",
        },
    }
    normalized_aliases = {
        "nanobanana2": "nano-banana-2",
        "nanobananatwo": "nano-banana-2",
        "nanobananapro": "nano-banana-pro",
    }
    requested = normalized_aliases.get(normalized, requested)
    if requested in variants:
        return variants[requested]
    for family, mapping in variants.items():
        if requested in mapping.values():
            return mapping
    return None


def resolve_model(model: Optional[str], size: Optional[str], aspect_ratio: Optional[str] = None) -> str:
    requested = (model or DEFAULT_MODEL).strip()
    orientation = detect_orientation(size, aspect_ratio)

    family = get_model_variants(requested)
    if family:
        if orientation == "ultrawide" and "ultrawide" not in family:
            raise HTTPException(status_code=400, detail=f"Model {requested} does not support 21:9. Use nano banana 2.")
        return family.get(orientation, family["landscape"])

    if requested in IMAGE_MODELS:
        if orientation == "ultrawide":
            raise HTTPException(status_code=400, detail=f"Model {requested} does not support 21:9. Use nano banana 2.")
        return requested

    raise HTTPException(status_code=400, detail=f"Unknown model: {requested}")


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def build_image_item(request: Request, path: Path, response_format: str) -> dict:
    if response_format == "b64_json":
        return {"b64_json": encode_image(path)}
    return {"url": str(request.base_url).rstrip("/") + f"/v1/files/{path.name}"}


def save_debug_payload(name: str, payload: Any) -> None:
    DEBUG_ROOT.mkdir(parents=True, exist_ok=True)
    path = DEBUG_ROOT / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def extract_prompt(messages: list[dict[str, Any]]) -> str:
    text_parts: list[str] = []
    for message in messages:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            text_parts.append(content)
            continue
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                item_type = (item.get("type") or "").lower()
                if item_type in {"text", "input_text"} and item.get("text"):
                    text_parts.append(str(item["text"]))
    prompt = "\n".join(part.strip() for part in text_parts if str(part).strip()).strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="No user prompt found in messages")
    return prompt


def extract_preferred_value(prompt: str, label: str) -> Optional[str]:
    patterns = [
        rf"{label}\s*:\s*([^\n\.]+)",
        rf"{label}\s*-\s*([^\n\.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def strip_preference_lines(prompt: str) -> str:
    cleaned = re.sub(r"(?im)^\s*preferred\s+(size|aspect\s*ratio)\s*[:\-]\s*[^\n]+\s*$", "", prompt)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_reference_image(messages: list[dict[str, Any]]) -> Optional[bytes]:
    for message in messages:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            item_type = (item.get("type") or "").lower()
            if item_type in {"image_url", "input_image"}:
                image_url = item.get("image_url")
                if isinstance(image_url, dict):
                    image_url = image_url.get("url")
                if isinstance(image_url, str) and image_url.startswith("data:") and "," in image_url:
                    return base64.b64decode(image_url.split(",", 1)[1])
    return None


def resolve_upscale(size: Optional[str], quality: Optional[str]) -> str:
    for raw in (quality, size):
        if not raw:
            continue
        value = str(raw).strip().lower()
        if value in {"4k"}:
            return "4k"
        if value in {"2k", "hd"}:
            return "2k"
        if value in {"1k", "standard", "default", "original"}:
            return "none"
    return "none"


def build_chat_response(
    request: Request,
    model_id: str,
    path: Path,
    response_format: str,
) -> dict:
    image_item = build_image_item(request, path, response_format)
    message_content = image_item.get("url") or image_item.get("b64_json") or ""
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": message_content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "data": [image_item],
    }


def build_api_info(base_url: str) -> dict:
    return {
        "url": f"{base_url}/v1",
        "api_key": get_api_key(),
        "recommended_models": [
            "nano banana2",
            "nano banana pro",
            "gemini-3.1-flash-image-landscape",
        ],
        "notes": [
            "Keep this computer powered on while the API is in use.",
            "Keep the Google Flow account signed in on this machine.",
            "21:9 is only supported by nano banana2.",
            "4K is slower and less stable than 1K/2K.",
        ],
    }


def clear_flow_state() -> None:
    config = get_config()
    config.token.st = ""
    config.token.at = ""
    config.token.at_expires = ""
    config.token.project_id = ""
    config.token.user_paygate_tier = "PAYGATE_TIER_NOT_PAID"
    config.save_token()


async def finalize_flow_setup(base_url: str) -> dict:
    st = await login_manager.extract_st()
    config = get_config()
    config.token.st = st
    config.token.at = ""
    config.token.at_expires = ""
    config.token.project_id = ""
    config.token.user_paygate_tier = "PAYGATE_TIER_NOT_PAID"
    config.save_token()

    generator = ImageGenerator()
    credits_info = await generator.check_credits()
    await generator.client.ensure_project()
    await login_manager.close()

    return {
        "success": True,
        "credits": credits_info.get("credits"),
        "tier": credits_info.get("userPaygateTier"),
        "api": build_api_info(base_url),
    }


app = FastAPI(title="Flow Image OpenAI-Compatible API", version="1.0.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/setup", response_class=HTMLResponse)
async def setup_page():
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Flow 本地配置</title>
  <style>
    :root { --bg:#f5f7fb; --card:#ffffff; --text:#111827; --muted:#6b7280; --border:#e5e7eb; --accent:#111827; --soft:#eef2ff; --ok:#0f766e; --warn:#b45309; --err:#b91c1c; }
    * { box-sizing:border-box; }
    body { font-family: Segoe UI, Microsoft YaHei, sans-serif; background:linear-gradient(180deg,#eef2ff 0%,#f8fafc 36%,#f5f7fb 100%); color:var(--text); margin:0; }
    .wrap { max-width: 980px; margin: 28px auto; padding: 0 18px 28px; }
    .hero { background:var(--card); border-radius:20px; padding:28px; box-shadow:0 14px 40px rgba(15,23,42,.08); border:1px solid rgba(229,231,235,.8); }
    h1 { margin:0 0 10px; font-size:32px; }
    .sub { color:var(--muted); margin:0; line-height:1.6; }
    .grid { display:grid; grid-template-columns: 1.2fr .8fr; gap:18px; margin-top:18px; }
    .card { background:var(--card); border:1px solid var(--border); border-radius:16px; padding:20px; box-shadow:0 8px 24px rgba(15,23,42,.04); }
    .title { font-size:18px; font-weight:700; margin:0 0 14px; }
    .step { display:flex; gap:12px; margin:12px 0; align-items:flex-start; }
    .num { width:28px; height:28px; border-radius:999px; background:var(--soft); display:flex; align-items:center; justify-content:center; font-weight:700; flex:none; }
    .step p { margin:2px 0 0; color:var(--muted); line-height:1.5; }
    .buttons { display:flex; flex-wrap:wrap; gap:10px; margin-top:16px; }
    button { border:none; border-radius:12px; padding:12px 16px; cursor:pointer; background:var(--accent); color:#fff; font-size:14px; font-weight:600; }
    button.secondary { background:#eef2f7; color:#111827; }
    button.warn { background:#f59e0b; }
    button.danger { background:#dc2626; }
    button:disabled { opacity:.55; cursor:not-allowed; }
    .status-grid { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:10px; }
    .pill { border:1px solid var(--border); border-radius:14px; padding:12px 14px; background:#fafafa; }
    .pill .label { font-size:12px; color:var(--muted); margin-bottom:6px; }
    .pill .value { font-weight:700; }
    .good { color:var(--ok); }
    .bad { color:var(--err); }
    .note { margin-top:14px; color:var(--muted); font-size:13px; line-height:1.6; }
    .api-box { display:grid; gap:12px; margin-top:8px; }
    .api-item { border:1px solid var(--border); background:#fafafa; border-radius:14px; padding:14px; }
    .api-item .label { font-size:12px; color:var(--muted); margin-bottom:8px; text-transform:uppercase; letter-spacing:.04em; }
    code { background:#f3f4f6; border-radius:8px; padding:2px 6px; word-break:break-all; }
    .models { display:flex; flex-wrap:wrap; gap:8px; }
    .model-chip { background:#eef2ff; color:#312e81; border-radius:999px; padding:7px 10px; font-size:13px; }
    ul { margin:10px 0 0 18px; color:var(--muted); padding:0; }
    .banner { border-radius:14px; padding:12px 14px; margin-top:14px; display:none; }
    .banner.ok { display:block; background:#ecfdf5; color:#065f46; }
    .banner.warn { display:block; background:#fff7ed; color:#9a3412; }
    .banner.err { display:block; background:#fef2f2; color:#991b1b; }
    .json { background:#0f172a; color:#e2e8f0; border-radius:14px; padding:16px; white-space:pre-wrap; font-size:12px; max-height:240px; overflow:auto; }
    @media (max-width: 860px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>Flow 本地自动配置</h1>
      <p class="sub">用户只需要登录 Google Flow。登录完成后，系统会自动同步 Token、验证账号、初始化项目，并给出最终可用的 API 信息。</p>
      <div id="banner" class="banner"></div>
    </div>
    <div class="grid">
      <div class="card">
        <div class="title">使用步骤</div>
        <div class="step"><div class="num">1</div><div><strong>打开登录页</strong><p>系统会自动打开 Flow 登录页。如果没有弹出，可以手动点击下面的按钮重新打开。</p></div></div>
        <div class="step"><div class="num">2</div><div><strong>登录 Google Flow</strong><p>在弹出的浏览器中登录你的 Google 会员账号。登录完成后，不需要再做额外操作。</p></div></div>
        <div class="step"><div class="num">3</div><div><strong>自动完成配置</strong><p>页面会自动检测登录状态并完成配置。必要时你也可以手动点击“重新同步”。</p></div></div>
        <div class="buttons">
          <button onclick="openLogin()">重新登录</button>
          <button class="secondary" onclick="finalizeSetup()">重新同步</button>
          <button class="secondary" onclick="refreshStatus()">刷新状态</button>
          <button class="danger" onclick="resetSetup()">重置配置</button>
        </div>
        <div class="note">推荐做法：用户只登录一次。成功后，把右侧显示的 URL、API Key 和模型信息提供给用户即可。</div>
      </div>
      <div class="card">
        <div class="title">当前状态</div>
        <div class="status-grid">
          <div class="pill"><div class="label">浏览器窗口</div><div class="value" id="browser_state">检测中</div></div>
          <div class="pill"><div class="label">登录状态</div><div class="value" id="login_state">检测中</div></div>
          <div class="pill"><div class="label">Session Token</div><div class="value" id="st_state">检测中</div></div>
          <div class="pill"><div class="label">Project</div><div class="value" id="project_state">检测中</div></div>
        </div>
        <div class="note">如果“登录状态”已经变成已检测到，但还没有出现 API 信息，可以点击“重新同步”。</div>
      </div>
    </div>
    <div class="grid">
      <div class="card">
        <div class="title">完成后的 API 信息</div>
        <div id="api_result">
          <div class="note">尚未完成自动配置。</div>
        </div>
      </div>
      <div class="card">
        <div class="title">调试信息</div>
        <div id="debug_json" class="json">加载中...</div>
      </div>
    </div>
  </div>
  <script>
    let finalized = false;
    function setBanner(type, text) {
      const el = document.getElementById('banner');
      if (!text) {
        el.className = 'banner';
        el.textContent = '';
        return;
      }
      el.className = `banner ${type}`;
      el.textContent = text;
    }
    function yn(value, okText = '已就绪', badText = '未就绪') {
      return value ? `<span class="good">${okText}</span>` : `<span class="bad">${badText}</span>`;
    }
    function renderStatus(data) {
      document.getElementById('browser_state').innerHTML = yn(data.browser_open, '已打开', '未打开');
      document.getElementById('login_state').innerHTML = yn(data.login_detected, '已检测到', '未检测到');
      document.getElementById('st_state').innerHTML = yn(data.has_st, '已保存', '未保存');
      document.getElementById('project_state').innerHTML = yn(data.project_ready, '已初始化', '未初始化');
      document.getElementById('debug_json').textContent = JSON.stringify(data, null, 2);
      if (data.login_detected && !data.has_st) {
        setBanner('warn', '已检测到 Flow 登录，正在等待自动同步或手动点击“重新同步”。');
      } else if (data.has_st && data.project_ready) {
        setBanner('ok', '配置已完成，可以直接复制右侧 API 信息给用户。');
      } else {
        setBanner('warn', '请先登录 Google Flow，完成后系统会自动配置。');
      }
    }
    function renderResult(data) {
      const api = data.api || {};
      const models = (api.recommended_models || []).map(m => `<span class="model-chip">${m}</span>`).join('');
      const notes = (api.notes || []).map(n => `<li>${n}</li>`).join('');
      document.getElementById('api_result').innerHTML = `
        <div class="api-box">
          <div class="api-item"><div class="label">URL</div><code>${api.url || ''}</code></div>
          <div class="api-item"><div class="label">API Key</div><code>${api.api_key || ''}</code></div>
          <div class="api-item"><div class="label">推荐模型</div><div class="models">${models}</div></div>
          <div class="api-item"><div class="label">账户信息</div><div>Credits: <strong>${data.credits ?? '-'}</strong><br/>Tier: <strong>${data.tier ?? '-'}</strong></div></div>
          <div class="api-item"><div class="label">必要说明</div><ul>${notes}</ul></div>
        </div>`;
    }
    async function refreshStatus() {
      const res = await fetch('/setup/status');
      const data = await res.json();
      renderStatus(data);
      if (!finalized && data.login_detected) {
        finalized = true;
        await finalizeSetup();
      }
    }
    async function openLogin() {
      const res = await fetch('/setup/open-login', { method: 'POST' });
      const data = await res.json();
      setBanner(data.success ? 'ok' : 'err', data.message || '已触发打开登录页。');
      await refreshStatus();
    }
    async function finalizeSetup() {
      document.getElementById('api_result').innerHTML = '<div class="note">正在自动配置，请稍候...</div>';
      const res = await fetch('/setup/finalize', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        renderResult(data);
        setBanner('ok', '自动配置完成。现在可以把 URL、API Key 和模型信息提供给用户。');
      } else {
        document.getElementById('api_result').innerHTML = `<div class="note">配置失败：${JSON.stringify(data)}</div>`;
        setBanner('err', '自动配置失败，请检查登录状态后重试。');
      }
      await refreshStatus();
    }
    async function resetSetup() {
      finalized = false;
      const res = await fetch('/setup/reset', { method: 'POST' });
      const data = await res.json();
      document.getElementById('api_result').innerHTML = '<div class="note">配置已重置。</div>';
      setBanner(data.success ? 'ok' : 'err', data.message || '配置已重置。');
      await refreshStatus();
    }
    refreshStatus();
    setInterval(refreshStatus, 4000);
  </script>
</body>
</html>
"""


@app.get("/setup/status")
async def setup_status(request: Request):
    config = get_config()
    return {
        "browser_open": await login_manager.is_open(),
        "login_detected": await login_manager.has_st_cookie(),
        "has_st": bool(config.token.st),
        "has_at": bool(config.token.at),
        "project_ready": bool(config.token.project_id),
        "api": build_api_info(str(request.base_url).rstrip("/")),
    }


@app.post("/setup/open-login")
async def setup_open_login():
    await login_manager.open("https://labs.google/fx/tools/flow")
    return {"success": True, "message": "Flow login browser opened. Please complete Google login there."}


@app.post("/setup/finalize")
async def setup_finalize(request: Request):
    return await finalize_flow_setup(str(request.base_url).rstrip("/"))


@app.post("/setup/reset")
async def setup_reset():
    clear_flow_state()
    await login_manager.close()
    return {"success": True, "message": "Flow state has been reset. You can log in again."}


@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    data = []
    for model_id in IMAGE_MODELS:
        data.append({"id": model_id, "object": "model", "owned_by": "flow-local"})
    return {"object": "list", "data": data}


@app.post("/v1/images/generations", dependencies=[Depends(verify_api_key)])
async def generate_image(request: Request, payload: ImageGenerationRequest):
    if payload.n != 1:
        raise HTTPException(status_code=400, detail="Only n=1 is supported")

    model_id = resolve_model(payload.model, payload.size, payload.aspect_ratio)
    upscale = resolve_upscale(payload.size, payload.quality)
    output_path = build_output_path("gen")

    generator = ImageGenerator()
    try:
        saved_path = await generator.generate(
            prompt=payload.prompt,
            model=model_id,
            output_path=str(output_path),
            upscale=upscale,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    path = Path(saved_path)
    return {
        "created": int(time.time()),
        "data": [build_image_item(request, path, (payload.response_format or "url").lower())],
    }


@app.post("/v1/images/edits", dependencies=[Depends(verify_api_key)])
async def edit_image(
    request: Request,
    image: UploadFile = File(...),
    prompt: str = Form(...),
    model: str = Form(default=DEFAULT_MODEL),
    size: Optional[str] = Form(default=None),
    aspect_ratio: Optional[str] = Form(default=None),
    quality: Optional[str] = Form(default="standard"),
    response_format: Optional[str] = Form(default="url"),
    n: int = Form(default=1),
):
    if n != 1:
        raise HTTPException(status_code=400, detail="Only n=1 is supported")

    model_id = resolve_model(model, size, aspect_ratio)
    upscale = resolve_upscale(size, quality)
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image file is empty")

    output_path = build_output_path("edit")
    generator = ImageGenerator()
    try:
        saved_path = await generator.generate(
            prompt=prompt,
            model=model_id,
            reference_image=image_bytes,
            output_path=str(output_path),
            upscale=upscale,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    path = Path(saved_path)
    return {
        "created": int(time.time()),
        "data": [build_image_item(request, path, (response_format or "url").lower())],
    }


@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: Request, payload: ChatCompletionRequest):
    if payload.stream:
        raise HTTPException(status_code=400, detail="stream=true is not supported")
    if payload.n not in (None, 1):
        raise HTTPException(status_code=400, detail="Only n=1 is supported")

    payload_dict = payload.model_dump()
    save_debug_payload("latest_chat_request.json", payload_dict)

    prompt = extract_prompt(payload.messages)
    inferred_size = extract_preferred_value(prompt, "preferred size")
    inferred_aspect_ratio = extract_preferred_value(prompt, "preferred aspect ratio")
    prompt = strip_preference_lines(prompt)
    reference_image = extract_reference_image(payload.messages)
    size = payload.size or inferred_size
    aspect_ratio = payload.aspect_ratio or inferred_aspect_ratio
    model_id = resolve_model(payload.model, size, aspect_ratio)
    upscale = resolve_upscale(size, payload.quality)
    output_path = build_output_path("chat")

    generator = ImageGenerator()
    try:
        saved_path = await generator.generate(
            prompt=prompt,
            model=model_id,
            reference_image=reference_image,
            output_path=str(output_path),
            upscale=upscale,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    path = Path(saved_path)
    response_format = (payload.response_format or "url").lower()
    return build_chat_response(request, model_id, path, response_format)


@app.get("/v1/files/{filename}")
async def get_generated_file(filename: str):
    path = OUTPUT_ROOT / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": {"message": exc.detail}})


def main():
    parser = argparse.ArgumentParser(description="Run OpenAI-compatible API wrapper for Flow Image CLI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("flow_cli.api_server:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
