import time
import random
from fastapi import FastAPI, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.metrics import REQUEST_COUNT, ERROR_COUNT, REQUEST_LATENCY
from app import simulator

app = FastAPI(title="OpsSentinel App")

START_TIME = time.time()


@app.middleware("http")
async def track_metrics(request, call_next):
    start = time.time()

    response = await call_next(request)

    duration = time.time() - start
    endpoint = request.url.path

    # Do not count Prometheus scraping as application traffic.
    if endpoint != "/metrics":
        REQUEST_COUNT.labels(
            endpoint=endpoint,
            method=request.method
        ).inc()

        REQUEST_LATENCY.labels(
            endpoint=endpoint
        ).observe(duration)

    return response


@app.get("/health")
def health():
    """Liveness check — is the process even running?"""
    return {"status": "alive"}


@app.get("/status")
def status():
    """Readiness-ish check — is the app in a state where it should serve traffic?"""
    state = simulator.get_state()
    healthy = not state["error_mode"] and state["cpu_percent"] < 95

    return {
        "healthy": healthy,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "state": state,
    }


@app.get("/metrics")
def metrics():
    """Prometheus scrapes this endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.post("/simulate/cpu")
def simulate_cpu(
    target_percent: float = 90.0,
    duration_seconds: int = 60
):
    return simulator.trigger_cpu_spike(
        target_percent,
        duration_seconds
    )


@app.post("/simulate/memory")
def simulate_memory(
    target_mb: float = 400.0,
    duration_seconds: int = 60
):
    return simulator.trigger_memory_spike(
        target_mb,
        duration_seconds
    )


@app.post("/simulate/errors")
def simulate_errors(enabled: bool = True):
    return simulator.set_error_mode(enabled)


@app.get("/work")
def do_work():
    """A normal business endpoint."""

    if simulator.is_error_mode():

        # ~70% failure rate when error mode is enabled.
        if random.random() < 0.7:
            ERROR_COUNT.labels(
                endpoint="/work"
            ).inc()

            return Response(
                content='{"error": "internal error"}',
                media_type="application/json",
                status_code=500
            )

    return {"result": "ok"}