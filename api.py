import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline import Pipeline
from plant.cost_model import compute_cost_per_hour

load_dotenv()

# ── Shared app state ──────────────────────────────────────────────────────────

pipeline: Pipeline | None = None
clients: list[WebSocket] = []

app_state: dict[str, Any] = {
    "running":       False,
    "tick_interval": 3,   # seconds between ticks
}


class ReadAgentRequest(BaseModel):
    query: str


class RuntimeSettingsRequest(BaseModel):
    voice: dict[str, Any] | None = None
    optimization: dict[str, Any] | None = None


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    pipeline = Pipeline()
    task = asyncio.create_task(tick_loop())
    yield
    task.cancel()


app = FastAPI(title="ChemBrain API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Tick loop ─────────────────────────────────────────────────────────────────

async def tick_loop():
    while True:
        if app_state["running"] and not pipeline.simulator.paused and not pipeline.simulator.finished:
            result = await asyncio.to_thread(pipeline.tick)
            await broadcast(build_payload(result))
        await asyncio.sleep(app_state["tick_interval"])


def build_payload(tick_result: dict | None = None) -> dict:
    state = pipeline.simulator.get_current_state()
    return {
        "type":          "tick",
        "hour":          pipeline.simulator.current_hour,
        "total_hours":   pipeline.simulator.total_hours,
        "state":         state,
        "alerts":        tick_result.get("alerts", []) if tick_result else [],
        "cost":          compute_cost_per_hour(state),
        "total_saving":  pipeline.total_saving,
        "new_decision":  tick_result.get("new_decision") if tick_result else None,
        "decisions":     pipeline.decisions[-30:],
        "running":       app_state["running"],
        "paused":        pipeline.simulator.paused,
        "finished":      pipeline.simulator.finished,
        "overrides":     pipeline.simulator.overrides,
        "voice_settings": pipeline.voice.get_settings(),
        "optimization_settings": pipeline.supervisor.get_optimization_settings(),
    }


async def broadcast(payload: dict):
    dead = []
    for ws in clients:
        try:
            await ws.send_text(json.dumps(payload, default=str))
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.remove(ws)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    # Send current state immediately on connect
    await websocket.send_text(json.dumps(build_payload(), default=str))
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        clients.remove(websocket)


# ── Control endpoints ─────────────────────────────────────────────────────────

@app.post("/api/start")
async def start():
    app_state["running"] = True
    pipeline.simulator.paused = False
    await broadcast(build_payload())
    return {"status": "started"}


@app.post("/api/pause")
async def pause():
    app_state["running"] = False
    await broadcast(build_payload())
    return {"status": "paused"}


@app.post("/api/reset")
async def reset():
    app_state["running"] = False
    pipeline.reset()
    await broadcast(build_payload())
    return {"status": "reset"}


@app.post("/api/override")
async def set_override(body: dict):
    pipeline.simulator.paused = body.get("paused", False)
    await broadcast(build_payload())
    return {"status": "ok"}


@app.post("/api/emergency-stop")
async def emergency_stop():
    app_state["running"] = False
    pipeline.simulator.paused = True
    pipeline.voice.speak(
        "Emergency stop activated. All autonomous control has been suspended. "
        "Please review plant state immediately."
    )
    await broadcast(build_payload())
    return {"status": "emergency_stop"}


@app.get("/api/state")
def get_state():
    return build_payload()


@app.post("/api/agents/read")
async def run_read_agent(body: ReadAgentRequest):
    try:
        result = await asyncio.to_thread(pipeline.reader.handle, body.query)
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/settings")
async def update_runtime_settings(body: RuntimeSettingsRequest):
    if body.voice:
        if "enabled" in body.voice:
            pipeline.voice.set_enabled(bool(body.voice["enabled"]))
        if isinstance(body.voice.get("voice_id"), str):
            pipeline.voice.set_voice_id(body.voice["voice_id"])

    if body.optimization:
        pipeline.supervisor.update_optimization_settings(body.optimization)

    payload = build_payload()
    await broadcast(payload)
    return {
        "voice_settings": payload["voice_settings"],
        "optimization_settings": payload["optimization_settings"],
    }


@app.post("/api/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language_code: str | None = Form(default=None),
):
    audio_bytes = await audio.read()
    try:
        result = await asyncio.to_thread(
            pipeline.voice.transcribe_audio,
            audio_bytes,
            audio.filename or "recording.webm",
            language_code,
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
