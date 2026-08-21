# Ops-Sentinel — Runbook

Detailed setup, verification, testing, and troubleshooting steps. See [README.md](./README.md) for overview and architecture.

All commands are PowerShell, run from the `ops-sentinel` root unless noted.

---

## Setup

### Prerequisites

- Git
- Python 3.10+
- Docker Desktop
- PowerShell

```powershell
python --version
docker --version
docker compose version
git --version
```

### 1. Clone

```powershell
git clone https://github.com/ishikasharma05/ops-sentinel.git
cd ops-sentinel
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Start FastAPI

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Keep this terminal running. App available at `http://localhost:8000`.

### 5. Start the monitoring stack

Open a **second** terminal:

```powershell
cd ops-sentinel
docker compose up -d
docker ps
```

Expected containers:
```
ops-sentinel-prometheus
ops-sentinel-grafana
ops-sentinel-alertmanager
```

### 6. Verify FastAPI

```powershell
Invoke-RestMethod http://localhost:8000/health
```
Expected:
```
status
------
alive
```

```powershell
Invoke-RestMethod http://localhost:8000/status
Invoke-RestMethod http://localhost:8000/metrics
```

### 7. Verify Prometheus is scraping the app

```powershell
(Invoke-RestMethod http://localhost:9090/api/v1/targets).data.activeTargets |
  Select-Object job, instance, health, lastError
```
Expected:
```
job           instance                    health
---           --------                    ------
ops-sentinel  host.docker.internal:8000  up
```

---

## Querying Metrics

```powershell
# Request count
(Invoke-RestMethod "http://localhost:9090/api/v1/query?query=app_requests_total").data.result |
  Select-Object metric, value

# CPU
(Invoke-RestMethod "http://localhost:9090/api/v1/query?query=app_simulated_cpu_percent").data.result |
  Select-Object metric, value

# Errors
(Invoke-RestMethod "http://localhost:9090/api/v1/query?query=app_errors_total").data.result |
  Select-Object metric, value
```

Raw metric examples as exposed on `/metrics`:
```
app_requests_total{endpoint="/work",method="GET"} 10
app_errors_total{endpoint="/work"} 11
```

---

## Grafana

Open `http://localhost:3000`. Dashboard is provisioned automatically from `grafana/dashboards/ops-sentinel.json` — you should not need to build any panel manually.

Panel reference is in [README.md](./README.md#grafana-dashboard-8-panels-code-defined).

---

## Alerting

### Test the CPU alert

Trigger a spike:
```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/simulate/cpu?target_percent=90&duration_seconds=120"
```
Expected:
```
status              target duration
------              ------ --------
cpu_spike_triggered 90.0   120
```

Confirm the value in Prometheus:
```powershell
(Invoke-RestMethod "http://localhost:9090/api/v1/query?query=app_simulated_cpu_percent").data.result |
  ForEach-Object { $_.value }
```

Check the rule state:
```powershell
(Invoke-RestMethod http://localhost:9090/api/v1/rules).data.groups |
  ForEach-Object { $_.rules } | Select-Object name, state, health
```
Expected while CPU is high:
```
name              state    health
----              -----    ------
HighSimulatedCPU  firing   ok
```

Confirm the firing alert directly:
```powershell
(Invoke-RestMethod "http://localhost:9090/api/v1/query?query=ALERTS%7Balertstate%3D%22firing%22%7D").data.result |
  ForEach-Object { $_.metric }
```
Expected:
```
__name__   : ALERTS
alertname  : HighSimulatedCPU
alertstate : firing
instance   : host.docker.internal:8000
job        : ops-sentinel
severity   : warning
```

### Verify resolution

Once the simulation duration elapses, re-check the CPU value (should drop back to baseline) and the rule state:
```powershell
(Invoke-RestMethod http://localhost:9090/api/v1/rules).data.groups |
  ForEach-Object { $_.rules } | Select-Object name, state, health
```
Expected:
```
name              state     health
----              -----     ------
HighSimulatedCPU  inactive  ok
```

Full loop confirmed: `normal → threshold breached → alert firing → value normalizes → alert resolved`.

### Test HTTP errors

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/simulate/errors?enabled=true"
```
Expected:
```
status             enabled
------             -------
error_mode_updated True
```

Generate traffic:
```powershell
1..20 | ForEach-Object {
    try { Invoke-RestMethod http://localhost:8000/work }
    catch { Write-Host "HTTP 500 generated" }
}
```

Check the error metric:
```powershell
(Invoke-RestMethod "http://localhost:9090/api/v1/query?query=app_errors_total").data.result |
  ForEach-Object { $_.metric; $_.value }
```

Disable when done:
```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/simulate/errors?enabled=false"
```

### Test memory simulation

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/simulate/memory?target_mb=400&duration_seconds=60"
(Invoke-RestMethod "http://localhost:9090/api/v1/query?query=app_simulated_memory_mb").data.result |
  ForEach-Object { $_.value }
```

---

## Troubleshooting

### FastAPI is not running

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  Select-Object LocalAddress, LocalPort, OwningProcess

Get-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess
```
Restart:
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Prometheus target is DOWN

```powershell
(Invoke-RestMethod http://localhost:9090/api/v1/targets).data.activeTargets |
  Select-Object job, instance, health, lastError
```
Then confirm FastAPI is actually reachable:
```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/metrics
```

### Grafana dashboard isn't loading

```powershell
docker ps
docker restart ops-sentinel-grafana
docker logs ops-sentinel-grafana --tail 50
Get-Item .\grafana\dashboards\ops-sentinel.json
```

### Grafana can't display Prometheus data

```powershell
docker ps
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=up"
Get-ChildItem .\grafana\provisioning -Recurse
```

### Alert doesn't fire

```powershell
(Invoke-RestMethod "http://localhost:9090/api/v1/query?query=app_simulated_cpu_percent").data.result |
  ForEach-Object { $_.value }

(Invoke-RestMethod http://localhost:9090/api/v1/rules).data.groups |
  ForEach-Object { $_.rules } | Select-Object name, state, health
```
Make sure CPU stays above the threshold for the full evaluation window — a spike that resolves before the window elapses won't trigger the alert.

---

## Stopping and Restarting

**Stop:**
```powershell
docker compose down
```
And `Ctrl+C` in the Uvicorn terminal.

**Restart:**
```powershell
# Terminal 1
cd ops-sentinel
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2
cd ops-sentinel
docker compose up -d
docker ps
```