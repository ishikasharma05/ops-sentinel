import time
import threading

from app.metrics import CPU_LOAD, MEMORY_LOAD


# In-memory state
_state = {
    "cpu_percent": 5.0,
    "memory_mb": 50.0,
    "error_mode": False,
}

_lock = threading.Lock()

# Initialize Prometheus gauges with the same starting values
CPU_LOAD.set(_state["cpu_percent"])
MEMORY_LOAD.set(_state["memory_mb"])


def trigger_cpu_spike(
    target_percent: float = 90.0,
    duration_seconds: int = 60
):
    """Simulate a CPU spike for a fixed duration."""

    def _run():
        with _lock:
            _state["cpu_percent"] = target_percent

        CPU_LOAD.set(target_percent)

        time.sleep(duration_seconds)

        with _lock:
            _state["cpu_percent"] = 5.0

        CPU_LOAD.set(5.0)

    threading.Thread(target=_run, daemon=True).start()

    return {
        "status": "cpu_spike_triggered",
        "target": target_percent,
        "duration": duration_seconds,
    }


def trigger_memory_spike(
    target_mb: float = 400.0,
    duration_seconds: int = 60
):
    """Simulate increased memory usage for a fixed duration."""

    def _run():
        with _lock:
            _state["memory_mb"] = target_mb

        MEMORY_LOAD.set(target_mb)

        time.sleep(duration_seconds)

        with _lock:
            _state["memory_mb"] = 50.0

        MEMORY_LOAD.set(50.0)

    threading.Thread(target=_run, daemon=True).start()

    return {
        "status": "memory_spike_triggered",
        "target": target_mb,
        "duration": duration_seconds,
    }


def set_error_mode(enabled: bool):
    with _lock:
        _state["error_mode"] = enabled

    return {
        "status": "error_mode_updated",
        "enabled": enabled,
    }


def is_error_mode() -> bool:
    with _lock:
        return _state["error_mode"]


def get_state():
    with _lock:
        return dict(_state)