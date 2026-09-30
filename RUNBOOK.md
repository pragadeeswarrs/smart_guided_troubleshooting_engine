# PRISM Smart Guided Troubleshooting Engine — Operations Runbook

Comprehensive operational guide for setting up, running, testing, and benchmarking the **PRISM Smart Guided Troubleshooting Engine** across Windows, macOS, and Linux.

---

## Table of Contents
1. [System Prerequisites](#1-system-prerequisites)
2. [Environment Configuration](#2-environment-configuration)
3. [Setup & Installation Instructions](#3-setup--installation-instructions)
   - [Windows (PowerShell & CMD)](#a-windows-powershell--cmd)
   - [macOS (Terminal / zsh)](#b-macos-terminal--zsh)
   - [Linux (Ubuntu / Debian / bash)](#c-linux-ubuntu--debian--bash)
4. [Running the Application](#4-running-the-application)
5. [Verification & Health Checks](#5-verification--health-checks)
6. [Interactive User Interfaces](#6-interactive-user-interfaces)
7. [Automated Benchmark & Evaluation Suite](#7-automated-benchmark--evaluation-suite)
8. [API Usage & Command Line Testing](#8-api-usage--command-line-testing)
9. [Operational Cache Management](#9-operational-cache-management)
10. [Troubleshooting & FAQs](#10-troubleshooting--faqs)

---

## 1. System Prerequisites

Before starting, ensure your system meets the minimum requirements:
- **Operating System:** Windows 10/11, macOS 12+ (Apple Silicon or Intel), or Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)
- **Python:** Version `3.10` or higher (`python --version`)
- **Package Manager:** `pip` (bundled with Python)
- **Version Control:** `git`
- **Internet Access:** Required during first startup to download lightweight semantic models (`all-MiniLM-L6-v2`) and connect to the Groq LLM API.

---

## 2. Environment Configuration

The engine requires an API key for the high-speed LLM service (Groq).

Create a file named `.env` in the repository root:
```ini
GROQ_API_KEY=your_groq_api_key_here
```
*(If you do not have an API key, get one from [console.groq.com](https://console.groq.com). Note that if the API key is missing or rate-limited, the engine automatically engages its deterministic, zero-fail offline fallback to ensure continuous evaluation).*

---

## 3. Setup & Installation Instructions

### A. Windows (PowerShell & CMD)

#### Using PowerShell:
```powershell
# 1. Clone repository (if not already local)
git clone https://github.com/pragadeeswarrs/smart_guided_troubleshooting_engine.git
cd smart_guided_troubleshooting_engine

# 2. Create Python virtual environment
python -m venv .venv

# 3. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# If script execution is restricted, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# 4. Install project dependencies
pip install -r requirements.txt
```

#### Using Command Prompt (cmd.exe):
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
```

---

### B. macOS (Terminal / zsh)

```bash
# 1. Clone repository
git clone https://github.com/pragadeeswarrs/smart_guided_troubleshooting_engine.git
cd smart_guided_troubleshooting_engine

# 2. Create Python virtual environment
python3 -m venv .venv

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Install project dependencies
pip install -r requirements.txt
```

---

### C. Linux (Ubuntu / Debian / bash)

```bash
# 1. Install system Python packages (if missing)
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git

# 2. Clone repository
git clone https://github.com/pragadeeswarrs/smart_guided_troubleshooting_engine.git
cd smart_guided_troubleshooting_engine

# 3. Create Python virtual environment
python3 -m venv .venv

# 4. Activate virtual environment
source .venv/bin/activate

# 5. Install project dependencies
pip install -r requirements.txt
```

---

## 4. Running the Application

Ensure your virtual environment is activated before launching the server:

```bash
# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

Start the FastAPI application with Uvicorn:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Server output:
```text
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

## 5. Verification & Health Checks

Verify that the service is running and passes **Gate G2**:

### Using curl:
```bash
curl -X GET http://127.0.0.1:8000/health
```

### Using PowerShell:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

**Expected Response (HTTP 200):**
```json
{"status": "ok"}
```

---

## 6. Interactive User Interfaces

Once the backend is running, access the following in your web browser:

1. **Samsung One UI Mobile Web Client:**
   - **URL:** [http://127.0.0.1:8000/ui/](http://127.0.0.1:8000/ui/)
   - **Features:** 
     - Adaptive One UI aesthetic (Ocean, Mint, Lilac, Peach themes).
     - Light/Dark mode auto-detection and toggle.
     - Collapsing dynamic header with scroll depth animation.
     - Real-time latency badge and cache hit flash feedback.
     - Slide-up bottom sheet with request diagnostics and cost breakdown.
     - Interactive follow-up CTA buttons for `auto` and `critical` Bixby deeplinks.

2. **Interactive OpenAPI / Swagger Documentation:**
   - **URL:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - Allows full interactive payload inspection and endpoint execution.

3. **ReDoc Documentation:**
   - **URL:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 7. Automated Benchmark & Evaluation Suite

Run the automated validation and benchmarking suite to verify compliance with **Gates G2–G5** and **Blocks A1–A5**:

```bash
python benchmark.py
```

### What `benchmark.py` Tests:
1. **Gate G2:** Health check status.
2. **Cold Start Latency:** First uncached request processing time (Target: P95 &le; 8000 ms).
3. **Repeat Latency & Caching:** 30 consecutive identical queries (Target: P95 &le; 300 ms, Cache Hit Rate &ge; 90%).
4. **Paraphrase Semantic Hit Rate:** 20 distinct colloquial variations (Target: Hit Rate &ge; 80%).
5. **Gate G5 URL Audit:** Regex audit for zero link leaks (`http`, `https`, `www`, `.com`, `.html`).
6. **Block A1–A5 Rules:** Goal regex format, 2–3 word titles, 5–7 word descriptions starting with `"It will"`, category sorting (`auto` &rarr; `manual` &rarr; `critical`), and query variation counts.

Generates or updates [metrics.md](metrics.md).

### Regenerating the 20-Scenario Evaluation File (`results.jsonl`):
```bash
python results_generator.py
```
This executes all 20 reference scenarios through the engine and exports the compliant JSONL evaluation dataset to `results.jsonl`.

---

## 8. API Usage & Command Line Testing

### Troubleshoot Endpoint: `POST /v1/troubleshoot`

#### Sample 1: Multi-Issue Custom Query (Auto + Manual + Critical)
```bash
curl -X POST http://127.0.0.1:8000/v1/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"query": "My Wi-Fi keeps disconnecting, router restart didn'\''t help, and battery is draining fast"}'
```

#### Sample 2: PowerShell Execution
```powershell
$body = @{ query = "Battery drains too fast on Galaxy S24 Ultra after update" } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/troubleshoot" -Method Post -Body $body -ContentType "application/json"
$response | ConvertTo-Json -Depth 6
```

#### Sample 3: Python Client
```python
import requests

payload = {"query": "Wi-Fi keeps disconnecting and dropping connection randomly"}
res = requests.post("http://127.0.0.1:8000/v1/troubleshoot", json=payload).json()

print(f"Latency: {res['meta']['latency_ms']}ms | Cache Hit: {res['meta']['cache_hit']}")
for ctx in res["response"]["contexts"]:
    print(f"\nContext: {ctx['title']} (Goal: {ctx['goal']})")
    for action in ctx["actions"]:
        dl = action["stepGroups"][0].get("actionableDeeplink") or {}
        print(f" - [{action['category'].upper()}] {action['actionName']} -> CTA: {dl.get('message', 'Manual Step')}")
```

---

## 9. Operational Cache Management

The engine employs a multi-tier semantic cache combining:
- **Tier 1:** Exact string lookup (< 0.05 ms)
- **Tier 2:** Normalized token overlap
- **Tier 3:** Vector cosine similarity on sentence embeddings (`all-MiniLM-L6-v2`)

### Clearing Cache (For Live Demo Video Reset):
To demonstrate a fresh cold start followed immediately by a cache hit:
```bash
curl -X DELETE http://127.0.0.1:8000/v1/cache
```
**Response:**
```json
{"cleared": 1}
```

---

## 10. Troubleshooting & FAQs

### Port 8000 already in use:
If another process is listening on port 8000:
- **Windows:**
  ```powershell
  Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
  ```
- **macOS / Linux:**
  ```bash
  kill -9 $(lsof -t -i:8000)
  ```
- Alternatively, launch on another port:
  ```bash
  uvicorn app.main:app --port 8080 --reload
  ```

### First-Time Model Download Delays:
On the very first request, `sentence-transformers` automatically downloads the lightweight embedding model weights (`all-MiniLM-L6-v2`, ~80MB) to `.cache_dir/`. Subsequent calls load from local disk in milliseconds.

### LLM API Rate Limits:
If your Groq free-tier token allowance is reached or network connectivity drops, the engine's built-in fallback automatically takes over:
- Context is retrieved via local hybrid vector search (`context_matcher.py`).
- Steps are structured and sanitized deterministically via `validator.py`.
- Deeplinks and preconditions are mapped via `search_service.py`.
- Zero 500 errors are returned, preserving 100% schema validity.
