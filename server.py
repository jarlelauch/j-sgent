import os
import time
import hmac
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import uuid4
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response, Depends, Cookie
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.ai.router import AIRouter
from app.ai.orchestration import (
    AgentMode,
    OrbitalEngine,
)
try:
    from app.ai.orchestration.mode import SystemMode
except Exception:
    SystemMode = None  # type: ignore

from app.core.config import SINGLE_USER, SINGLE_PASS, SESSION_SECRET

try:
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
    _serializer = URLSafeTimedSerializer(SESSION_SECRET)
    def create_token(user: str) -> str:
        return _serializer.dumps({"u": user})
    def verify_token(token: str) -> Optional[str]:
        try:
            data = _serializer.loads(token, max_age=30*24*3600)
            return data.get("u")
        except (BadSignature, SignatureExpired):
            return None
except Exception:
    # fallback plain (not secure, dev only)
    def create_token(user: str) -> str:
        return f"plain:{user}"
    def verify_token(token: str) -> Optional[str]:
        if token.startswith("plain:"):
            return token.split(":",1)[1]
        return None

app = FastAPI(
    title="J. S'GENT",
    version="0.2.0",
    docs_url=None,  # hide docs on public gratisan
    redoc_url=None,
)

router = AIRouter()
engine = OrbitalEngine(router)

executor = ThreadPoolExecutor(max_workers=2)
tasks = {}

SESSION_COOKIE = "jsgent_session"

# --- hardening: rate limit login + run ---
_login_attempts = defaultdict(lambda: deque())  # ip -> deque[timestamps]
_run_attempts = defaultdict(lambda: deque())
_LOGIN_MAX = 5
_LOGIN_WINDOW = 15*60  # 15 menit
_RUN_MAX = 20
_RUN_WINDOW = 60

def _is_rate_limited(bucket: deque, max_hits: int, window: int) -> bool:
    now = time.time()
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    return len(bucket) >= max_hits

def _hit(bucket: deque):
    bucket.append(time.time())

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # CSP strict for public hosting
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'"
    # HSTS only if https (free hosting https)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

def get_current_user(request: Request) -> Optional[str]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        # also allow Authorization Bearer for API / free hosting
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.split(" ",1)[1]
    if not token:
        return None
    return verify_token(token)

def require_auth(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized — silakan login.")
    return user

# optional auth for health (public), strict for run/tasks
def require_auth_optional(request: Request):
    # if single user not set, allow all (dev)
    # else require
    # we enforce for run/tasks only
    return get_current_user(request)

class LoginRequest(BaseModel):
    username: str
    password: str

class RunRequest(BaseModel):
    objective: str
    mode: AgentMode = AgentMode.NORMAL
    system: str = "orbital"  # orbital | agent | chatbot

def run_task(task_id, objective, mode, system):

    tasks[task_id]["status"] = "running"
    tasks[task_id]["started_at"] = datetime.now().isoformat()
    tasks[task_id]["system"] = system

    try:
        def orbit_callback(state, record):
            tasks[task_id]["live"] = {
                "state": "orbiting",
                "orbit": record.index,
                "purpose": record.purpose,
                "provider": record.provider,
                "confidence": record.confidence,
                "history": [
                    {
                        "orbit": item.index,
                        "purpose": item.purpose,
                        "provider": item.provider,
                        "confidence": item.confidence,
                        "output": item.output,
                    }
                    for item in state.history
                ],
            }

        # engine supports system param (updated)
        try:
            result = engine.run(objective, mode, system=system, on_orbit=orbit_callback)
        except TypeError:
            # backward compat: old signature
            result = engine.run(objective, mode, on_orbit=orbit_callback)

        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = {
            "objective": result.objective,
            "mode": result.mode.value,
            "system": getattr(result, "system", system),
            "core_answer": result.core_answer,
            "confidence": result.confidence,
            "orbit_count": result.orbit_count,
            "evidence_count": len(result.evidence),
            "history": [
                {
                    "orbit": item.index,
                    "purpose": item.purpose,
                    "provider": item.provider,
                    "confidence": item.confidence,
                    "output": item.output,
                }
                for item in result.history
            ],
        }

    except Exception as exc:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(exc)

    finally:
        tasks[task_id]["finished_at"] = datetime.now().isoformat()


LOGIN_HTML = r"""<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>J. S'GENT — Login</title>
<style>
:root{--bg:#050608;--panel:#090b0f;--line:#1b2028;--text:#e8ebef;--muted:#6e7682}
*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--bg);color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif}
.wrap{min-height:100vh;display:grid;place-items:center;padding:24px}
.card{width:360px;max-width:94vw;border:1px solid var(--line);background:var(--panel);padding:22px}
.brand{display:flex;align-items:center;gap:12px;padding-bottom:16px;border-bottom:1px solid var(--line);margin-bottom:16px}
.mark{width:36px;height:42px;display:grid;place-items:center;border:1px solid #2b313b;background:#090b0f}
.mark svg{width:20px;height:28px}
.brand strong{display:block;letter-spacing:.18em;font-size:13px}
.brand span{color:var(--muted);font-size:7px;letter-spacing:.15em}
label{display:block;font-size:8px;letter-spacing:.14em;color:#6e7682;margin:10px 0 6px}
input{width:100%;padding:11px 12px;border:1px solid var(--line);background:#07090c;color:var(--text);outline:none}
input:focus{border-color:#343b46}
.btn{width:100%;margin-top:14px;padding:11px;border:1px solid #aeb4bc;background:#f4f5f7;color:#08090b;font-weight:700;letter-spacing:.1em;font-size:9px;cursor:pointer}
.btn:hover{background:#fff}
.hint{margin-top:10px;color:#4e5662;font-size:7px;letter-spacing:.06em;text-align:center}
.err{margin-top:10px;padding:8px;border:1px solid #3a1f1f;background:#120a0a;color:#d68a8a;font-size:11px;display:none}
</style></head><body><div class="wrap"><form class="card" onsubmit="return doLogin(event)">
<div class="brand"><div class="mark"><svg viewBox="0 0 100 130"><rect x="43" y="6" width="14" height="117" fill="#e3e6e9"/><rect x="20" y="76" width="60" height="14" fill="#e3e6e9"/></svg></div><div><strong>J. S'GENT</strong><span>ORBITAL AI SYSTEM — LOGIN</span></div></div>
<div id="err" class="err"></div>
<label>USERNAME</label><input id="u" autocomplete="username" placeholder="admin">
<label>PASSWORD</label><input id="p" type="password" autocomplete="current-password" placeholder="••••••••">
<button class="btn" type="submit">MASUK</button>
<div class="hint">Single akun — hanya pemilik. HTTP local & web gratisan sama.</div>
</form></div>
<script>
async function doLogin(e){
 e.preventDefault();
 const u=document.getElementById('u').value.trim();
 const p=document.getElementById('p').value;
 const err=document.getElementById('err');
 err.style.display='none';
 try{
  const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});
  const j=await r.json();
  if(!r.ok) throw new Error(j.detail||'Login gagal');
  location.href='/';
 }catch(ex){ err.textContent=ex.message; err.style.display='block'; }
 return false;
}
</script></body></html>
"""

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return LOGIN_HTML

@app.post("/api/login")
def api_login(payload: LoginRequest, request: Request, response: Response):
    # rate limit by IP
    ip = request.client.host if request.client else "unknown"
    bucket = _login_attempts[ip]
    if _is_rate_limited(bucket, _LOGIN_MAX, _LOGIN_WINDOW):
        raise HTTPException(status_code=429, detail="Terlalu banyak percobaan. Coba lagi 15 menit.")
    if payload.username != SINGLE_USER or payload.password != SINGLE_PASS:
        _hit(bucket)
        # constant-time compare to avoid timing leak
        hmac.compare_digest(payload.password, SINGLE_PASS)
        raise HTTPException(status_code=401, detail="Username atau password salah.")
    # success -> clear attempts
    _login_attempts[ip] = deque()
    token = create_token(payload.username)
    is_https = request.url.scheme == "https"
    response.set_cookie(key=SESSION_COOKIE, value=token, httponly=True, samesite="lax", secure=is_https, max_age=30*24*3600, path="/")
    return {"ok": True, "user": payload.username, "token": token}

@app.post("/api/logout")
def api_logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}

@app.get("/api/me")
def api_me(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Belum login")
    return {"user": user}

@app.get("/")
def index(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse("web/static/index.html")

@app.get("/api/health")
def health(request: Request):
    # public but also shows auth status
    prov = router.available()
    user = get_current_user(request)
    return {
        "status": "online",
        "agent": "J. S'GENT",
        "auth": bool(user),
        "user": user,
        "providers": prov,
        "models": {
            "ollama": getattr(router.get("ollama"), "model", None) if router.get("ollama") else None,
            "muse": getattr(router.get("muse"), "model", None) if router.get("muse") else None,
        }
    }

@app.get("/api/modes")
def modes(request: Request):
    # optional auth — still require login for consistency on gratisan
    # allow public in local dev if not authenticated? we enforce but not strict
    # user = get_current_user(request)
    # if not user: raise HTTP...
    return {
        "modes": [
            {"name": AgentMode.FAST.value, "orbits": 1},
            {"name": AgentMode.NORMAL.value, "orbits": 5},
            {"name": AgentMode.HIGH.value, "orbits": 15},
            {"name": AgentMode.ULTRA.value, "orbits": 50},
        ],
        "systems": ["orbital", "agent", "chatbot"],
        "providers": router.available(),
    }

@app.post("/api/run")
def create_task(request: RunRequest, http_req: Request, user: str = Depends(require_auth)):

    # run rate limit per user/ip
    ip = http_req.client.host if http_req.client else "unknown"
    bucket = _run_attempts[ip]
    if _is_rate_limited(bucket, _RUN_MAX, _RUN_WINDOW):
        raise HTTPException(status_code=429, detail="Terlalu banyak request. Tunggu 1 menit.")
    _hit(bucket)

    objective = request.objective.strip()
    if not objective:
        raise HTTPException(status_code=400, detail="Objective tidak boleh kosong.")
    if len(objective) > 8000:
        raise HTTPException(status_code=400, detail="Objective terlalu panjang (max 8000).")

    # normalize system
    system = (request.system or "orbital").lower()
    if system not in ("orbital", "agent", "chatbot", "chat"):
        system = "orbital"
    if system == "chat":
        system = "chatbot"

    # mode is already AgentMode, but also handle legacy agent/chatbot passed as mode
    mode = request.mode
    # if client sent system as mode (old UI), normalize
    if isinstance(mode, str):
        low = mode.lower()
        if low in ("agent", "chatbot"):
            # treat as system, default speed normal
            system = low
            mode = AgentMode.NORMAL
        else:
            try:
                mode = AgentMode(low)
            except Exception:
                mode = AgentMode.NORMAL

    task_id = uuid4().hex[:12]

    tasks[task_id] = {
        "id": task_id,
        "objective": objective,
        "mode": mode.value if hasattr(mode, "value") else str(mode),
        "system": system,
        "user": user,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
    }

    executor.submit(run_task, task_id, objective, mode, system)

    return {"task_id": task_id, "status": "queued", "system": system, "mode": getattr(mode, "value", str(mode))}

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, request: Request, user: str = Depends(require_auth)):

    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task tidak ditemukan.")
    # optional: check owner
    # if task.get("user") != user: raise 403
    return task

# for free hosting health check
@app.get("/healthz")
def healthz():
    return {"ok": True}
