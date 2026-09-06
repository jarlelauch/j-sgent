from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.ai.router import AIRouter
from app.ai.orchestration import (
    AgentMode,
    OrbitalEngine,
)


app = FastAPI(
    title="J. S'GENT",
    version="0.1.0",
)


router = AIRouter()
engine = OrbitalEngine(router)

executor = ThreadPoolExecutor(
    max_workers=2
)

tasks = {}


class RunRequest(BaseModel):
    objective: str
    mode: AgentMode = AgentMode.NORMAL


def run_task(task_id, objective, mode):

    tasks[task_id]["status"] = "running"
    tasks[task_id]["started_at"] = (
        datetime.now().isoformat()
    )

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

        result = engine.run(
            objective,
            mode,
            on_orbit=orbit_callback,
        )

        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = {

            "objective":
                result.objective,

            "mode":
                result.mode.value,

            "core_answer":
                result.core_answer,

            "confidence":
                result.confidence,

            "orbit_count":
                result.orbit_count,

            "evidence_count":
                len(result.evidence),

            "history": [
                {
                    "orbit":
                        item.index,

                    "purpose":
                        item.purpose,

                    "provider":
                        item.provider,

                    "confidence":
                        item.confidence,

                    "output":
                        item.output,
                }

                for item in result.history
            ],
        }

    except Exception as exc:

        tasks[task_id]["status"] = "failed"

        tasks[task_id]["error"] = str(exc)

    finally:

        tasks[task_id]["finished_at"] = (
            datetime.now().isoformat()
        )


@app.get("/")
def index():

    return FileResponse(
        "web/static/index.html"
    )


@app.get("/api/health")
def health():

    return {
        "status": "online",
        "agent": "J. S'GENT",
        "providers": router.available(),
    }


@app.get("/api/modes")
def modes():

    return {
        "modes": [
            {
                "name": AgentMode.FAST.value,
                "orbits": 1,
            },
            {
                "name": AgentMode.NORMAL.value,
                "orbits": 5,
            },
            {
                "name": AgentMode.HIGH.value,
                "orbits": 15,
            },
            {
                "name": AgentMode.ULTRA.value,
                "orbits": 50,
            },
        ]
    }


@app.post("/api/run")
def create_task(request: RunRequest):

    objective = request.objective.strip()

    if not objective:

        raise HTTPException(
            status_code=400,
            detail="Objective tidak boleh kosong.",
        )

    task_id = uuid4().hex[:12]

    tasks[task_id] = {
        "id": task_id,
        "objective": objective,
        "mode": request.mode.value,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
    }

    executor.submit(
        run_task,
        task_id,
        objective,
        request.mode,
    )

    return {
        "task_id": task_id,
        "status": "queued",
    }


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):

    task = tasks.get(task_id)

    if task is None:

        raise HTTPException(
            status_code=404,
            detail="Task tidak ditemukan.",
        )

    return task
