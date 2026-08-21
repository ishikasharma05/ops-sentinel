# Ops-Sentinel

Application observability and monitoring project built with FastAPI, Prometheus, Grafana, and Alertmanager.

> **Environment note:** Setup/verification commands throughout this repo are written for **Windows PowerShell**. The FastAPI app runs on the host; Prometheus, Grafana, and Alertmanager run in Docker. The stack is not yet fully containerized end-to-end — see [Roadmap](#roadmap).

For full setup steps, verification commands, alert testing, and troubleshooting, see **[RUNBOOK.md](./RUNBOOK.md)**.

---

## Overview

Ops-Sentinel demonstrates a real-time application monitoring pipeline: metrics collection, visualization, and alerting.

- FastAPI exposes Prometheus-compatible metrics at `/metrics`.
- Prometheus scrapes those metrics on an interval and evaluates alert rules against them.
- Grafana renders a code-defined dashboard (provisioned from JSON, not built by hand in the UI).
- Alertmanager handles alert routing.
- `/simulate/*` endpoints (CPU, memory, errors) let you exercise the alerting pipeline without waiting for a real production failure.

## Architecture

```text
                         WINDOWS HOST
┌───────────────────────────────────────────────────────────┐
│                                                             │
│                    FastAPI Application                     │
│                       localhost:8000                       │
│                             │                               │
│                             │ /metrics                      │
│                             ▼                               │
│                  ┌──────────────────────┐                  │
│                  │      Prometheus      │                  │
│                  │        :9090         │                  │
│                  └──────────┬───────────┘                  │
│                             │                               │
│                    ┌────────┴────────┐                     │
│                    ▼                 ▼                     │
│             ┌─────────────┐   ┌──────────────┐             │
│             │   Grafana   │   │ Alertmanager │             │
│             │    :3000    │   │    :9093     │             │
│             └─────────────┘   └──────────────┘             │
│                                                             │
└───────────────────────────────────────────────────────────┘
```

**Flow:** FastAPI → `/metrics` → Prometheus scrapes + stores time series + evaluates alert rules → Grafana visualizes.

## Tech Stack

| Technology | Purpose |
|---|---|
| Python / FastAPI | Application & API |
| Uvicorn | ASGI server |
| Prometheus | Metrics collection, alert evaluation |
| Grafana | Dashboards |
| Alertmanager | Alert routing |
| Docker | Monitoring infrastructure (not the app itself) |
| PowerShell | Setup and verification on Windows |

## Project Structure

```
ops-sentinel/
├── app/
│   ├── main.py
│   ├── metrics.py
│   └── simulator.py
├── prometheus/
│   ├── prometheus.yml
│   └── rules/alerts.yml
├── grafana/
│   ├── dashboards/ops-sentinel.json
│   └── provisioning/
│       ├── dashboards/dashboards.yml
│       └── datasources/datasource.yml
├── docker-compose.yml
├── requirements.txt
├── Dockerfile
├── README.md
└── RUNBOOK.md
```

---

## Quickstart

```powershell
git clone https://github.com/ishikasharma05/ops-sentinel.git
cd ops-sentinel

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Terminal 1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2
docker compose up -d
```

| Service | URL |
|---|---|
| FastAPI | http://localhost:8000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| Alertmanager | http://localhost:9093 |

Full step-by-step (venv activation issues, dependency install, expected outputs, container checks) is in **[RUNBOOK.md](./RUNBOOK.md#setup)**.

## Metrics Exposed

| Metric | Type | Description |
|---|---|---|
| `app_requests_total` | Counter | Requests by endpoint/method |
| `app_errors_total` | Counter | Errors by endpoint |
| `app_simulated_cpu_percent` | Gauge | Simulated CPU load |
| `app_simulated_memory_mb` | Gauge | Simulated memory usage |
| `app_request_latency_seconds` | Histogram | Request latency |

`/metrics` is excluded from request tracking so Prometheus's own scrapes don't inflate the request count.

## Grafana Dashboard (8 panels, code-defined)

Provisioned from `grafana/dashboards/ops-sentinel.json`.

| Panel | Metric |
|---|---|
| Total Requests | `sum(app_requests_total)` |
| HTTP Error Rate | `100 * sum(rate(app_errors_total[5m])) / clamp_min(sum(rate(app_requests_total[5m])), 1e-9)` |
| Application Health | `up{job="ops-sentinel"}` (1=up, 0=down) |
| CPU Threshold | `app_simulated_cpu_percent` |
| Active Alerts | `sum(ALERTS{alertstate="firing"})` |
| Avg Request Latency (ms) | `1000 * sum(rate(app_request_latency_seconds_sum[5m])) / clamp_min(sum(rate(app_request_latency_seconds_count[5m])), 1e-9)` |
| Request Rate Over Time | `sum(rate(app_requests_total[1m]))` |
| CPU Over Time | `app_simulated_cpu_percent` |

## Alerting

**Rule:** `HighSimulatedCPU` — fires when `app_simulated_cpu_percent > 80` for the configured evaluation window.

Full firing/resolution walkthrough with expected command output: **[RUNBOOK.md](./RUNBOOK.md#alerting)**.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/status` | App status |
| GET | `/metrics` | Prometheus metrics |
| GET | `/work` | Normal traffic endpoint |
| POST | `/simulate/cpu` | Simulate CPU load |
| POST | `/simulate/memory` | Simulate memory load |
| POST | `/simulate/errors` | Toggle error simulation |

---

## Current Status

**Implemented and manually verified locally:**
- FastAPI app with health/status endpoints
- Prometheus metrics (requests, errors, latency, simulated CPU/memory)
- Prometheus scraping + alert rule evaluation
- Grafana dashboard provisioning (8 panels, code-defined)
- `HighSimulatedCPU` alert — firing and resolution tested via simulation endpoints
- HTTP error simulation

**Not yet done:**
- FastAPI is not containerized (runs on host, not in Docker)
- No CI/CD
- No persistent storage for Prometheus/Grafana (data lost on container recreation)
- No automated test suite — verification is manual/interactive, run and confirmed by hand, not by a script

## Roadmap

- Dockerize the FastAPI app; run the full stack with one `docker compose up`
- Add Docker health checks and persistent volumes for Prometheus/Grafana
- Additional alerts: memory threshold, latency threshold, HTTP error rate
- Alertmanager notification routing (currently receives alerts but doesn't notify anywhere)
- GitHub Actions CI/CD
- Structured logging → Loki; distributed tracing → Tempo
- Deploy to AWS / Kubernetes
- HTTPS + authentication

---

## Author

Ishika Sharma