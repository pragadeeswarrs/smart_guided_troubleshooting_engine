# PRISM: Smart Guided Troubleshooting Engine

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-MiniLM-EE4C2C.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Samsung PRISM](https://img.shields.io/badge/Samsung%20PRISM-GenAI%20Theme%202-1428A0.svg)](#)
[![Submission Tag](https://img.shields.io/badge/GitHub%20Tag-PRISM__GENAI__HACKATHON__Y2026-orange.svg)](#)

> **An intelligent, context-aware smartphone troubleshooting engine that transforms natural language user complaints into structured, actionable recovery plans with native Samsung Bixby deeplinks, precondition validations, and sub-millisecond semantic caching.**

Developed for the **Samsung PRISM Hackathon — Theme 2: Smart Guided Troubleshooting Engine**.

---

## 📑 Quick Navigation
- [✨ Key Features](#-key-features)
- [📱 Visual Preview & UI](#-visual-preview--ui)
- [📦 System Requirements](#-system-requirements)
- [⚡ Quick Start & Installation](#-quick-start--installation)
- [💡 Usage Examples](#-usage-examples)
- [🏗️ System Architecture](#️-system-architecture)
- [📊 Evaluation & Benchmarks](#-evaluation--benchmarks)
- [📋 Hackathon Submission Checklist](#-hackathon-submission-checklist)
- [🤖 AI Disclosure](#-ai-disclosure)
- [📄 License & Authors](#-license--authors)

---

## ✨ Key Features

- **Hybrid Semantic Retrieval:** Combines dense neural embeddings (`all-MiniLM-L6-v2`) via ChromaDB and probabilistic lexical scoring (`rank-bm25`) to accurately ground user complaints against the official Samsung SIIS knowledge base.
- **Multi-Intent / Composite Complaint Synthesis:** Automatically detects and resolves multiple simultaneous device problems (e.g. Wi-Fi dropping + battery drain) within a single unified plan.
- **Tri-Category Action Classification (`auto`, `manual`, `critical`):**
  - **`auto`:** Navigates directly to device settings via Samsung Bixby deeplinks (e.g. `bixby://com.samsung.android.settings.connections.wifi`).
  - **`manual`:** Formats clear hardware and environmental inspections (e.g., cleaning sensor pinholes, router power cycles).
  - **`critical`:** Safeguards high-risk procedures (e.g. `bixby://com.samsung.android.settings.general.reset_network`, factory reset) with distinct visual warning badges.
- **Strict Sorting & Fallback (Block A2):** Actions are deterministically sorted `auto` &rarr; `manual` &rarr; `critical`. Unmatched auto actions fall back to `bixby://dummy_positive`.
- **Precondition & Validation Rules:** Binds real-time verification rules (e.g., `wifi_enabled == true`, `power_saving_mode == true`, `screen_brightness > 100`) directly to action steps.
- **Sub-Millisecond Multi-Tier Semantic Cache:** Employs exact hash, token overlap, and cosine vector distance thresholds to deliver repeat/paraphrased queries in **&le; 1.7 ms** with **$0.00** LLM cost.
- **Zero URL Leak Policy (Gate G5):** Programmatically scrubs all web URLs, markdown links, and HTML anchors to maintain self-contained, native device privacy.
- **Samsung One UI Web Experience:** Ergonomic mobile-first interface featuring collapsing header transitions, theme switcher (Ocean, Mint, Lilac, Peach), real-time latency diagnostics, and clickable Bixby follow-up action buttons.

---

## 📱 Visual Preview & UI

The engine includes a native Samsung One UI web client located at `ui/index.html` (served at `http://127.0.0.1:8000/ui/`):

```text
+-----------------------------------------------------------+
|                     Galaxy Support                        |
|        "Describe the problem and get guided steps"        |
+-----------------------------------------------------------+
|  User: "My Wi-Fi keeps disconnecting, router restart      |
|         didn't help, and battery is draining fast"        |
|                                                           |
|  [Card 1: Battery Settings]                               |
|   1. [AUTO] Battery Configuration                         |
|      "It will configure battery settings on device"       |
|      [ CTA: Open Power Saving ]                           |
|   2. [MANUAL] Battery Inspection                          |
|      "It will guide your manual hardware inspection"      |
|                                                           |
|  [Card 2: Wi-Fi Connection Settings]                      |
|   1. [AUTO] Wi-Fi Connection Configuration                |
|      "It will configure wi-fi connection settings on"     |
|      [ CTA: Open Wi-Fi Settings ]                         |
|   2. [MANUAL] Wi-Fi Connection Recovery                   |
|      "It will perform device recovery and reboot"         |
|   3. [CRITICAL] Wi-Fi Connection Reset                    |
|      "It will guide your manual hardware inspection"      |
|      [ CTA: Reset Network Settings ]                      |
+-----------------------------------------------------------+
|  [ Latency: 0.8 ms | Cache Hit ]   [ Dark Mode: Toggle ]  |
+-----------------------------------------------------------+
```

- **Demo Video:** [Watch the Full Demonstration Video](https://drive.google.com/file/d/1gyb0jvfj5BSKe0tgpVsmlruWP-htE-yi/view?usp=sharing)
- **Presentation Deck:** [View the PRISM Presentation Slides](./PRISM_Submission_PPT.pptx)
- **AI Disclosure:** [View the AI Disclosure Doc](./AI_Disclosure.docx)


---

## 📦 System Requirements

### Python & Environment
- **Python:** `3.10` or higher
- **Package Manager:** `pip`
- **Memory:** &ge; 4 GB RAM recommended (for local MiniLM neural embeddings)

### Python Dependencies (`requirements.txt`)
| Library | Version Range | Purpose |
|---|---|---|
| `fastapi` | `>=0.110, <1.0` | High-performance asynchronous REST API framework |
| `uvicorn[standard]` | `>=0.29, <1.0` | Production ASGI web server |
| `pydantic` | `>=2.6, <3.0` | Strict Appendix A contract schema validation |
| `diskcache` | `>=5.6, <6.0` | Multi-tier persistent semantic caching |
| `sentence-transformers` | Latest | Local 384-dim dense embeddings (`all-MiniLM-L6-v2`) |
| `chromadb` | Latest | Local high-speed vector database |
| `rank_bm25` | Latest | Probabilistic BM25 Okapi lexical retrieval |
| `openai` | Latest | Groq LLM async API integration |
| `httpx` | `>=0.27, <1.0` | Async HTTP client for benchmarking & evaluation |
| `python-dotenv` | Latest | Environment variable configuration |

---

## ⚡ Quick Start & Installation

Detailed multi-OS setup (Windows, macOS, Linux) is documented in [RUNBOOK.md](RUNBOOK.md).

### 1. Clone the Repository
```bash
git clone https://github.com/pragadeeswarrs/smart_guided_troubleshooting_engine.git
cd smart_guided_troubleshooting_engine
```

### 2. Configure Environment Variables
Create a `.env` file in the project root:
```ini
GROQ_API_KEY=your_groq_api_key_here
```
*(The engine includes an offline deterministic fallback; if no key is present or quota is exhausted, evaluation continues without interruption).*

### 3. Setup Virtual Environment & Install Dependencies

#### On Windows:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Start the Engine
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **One UI Interactive Web App:** [http://127.0.0.1:8000/ui/](http://127.0.0.1:8000/ui/)
- **Health Check:** `curl http://127.0.0.1:8000/health`

---

## 💡 Usage Examples

### 1. Multi-Issue Master Query (`POST /v1/troubleshoot`)
Demonstrates multi-intent detection, all 3 action categories (`auto`, `manual`, `critical`), and Bixby deeplinks:

```bash
curl -X POST http://127.0.0.1:8000/v1/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"query": "My Wi-Fi keeps disconnecting, router restart didn'\''t help, and battery is draining fast"}'
```

**JSON Response Envelope (Strict Appendix A Contract):**
```json
{
  "query": "My Wi-Fi keeps disconnecting, router restart didn't help, and battery is draining fast",
  "query_variations": [
    "Wi-Fi keeps dropping connection and battery is draining super fast",
    "Battery dying fast and Wi-Fi disconnecting continuously",
    "Samsung Galaxy Wi-Fi connection drops and fast battery drain",
    "..."
  ],
  "response": {
    "contexts": [
      {
        "title": "Battery Settings",
        "goal": "Follow these steps to perform this Battery Troubleshooting.",
        "score": 0.95,
        "actions": [
          {
            "actionName": "Battery Configuration",
            "description": "It will configure battery settings on device",
            "category": "auto",
            "stepGroups": [
              {
                "steps": [
                  "Battery Optimization: To fix fast battery drain, open Settings and go to Battery and Device Care.",
                  "Tap on Battery to view power usage per app."
                ],
                "actionableDeeplink": {
                  "deeplink": "bixby://com.samsung.android.settings.battery.powersaving",
                  "description": "It will enable battery saving mode",
                  "message": "Power Saving"
                }
              }
            ]
          }
        ]
      },
      {
        "title": "Wi-Fi Connection Settings",
        "goal": "Follow these steps to perform this Wi-Fi Connection Troubleshooting.",
        "score": 0.95,
        "actions": [
          {
            "actionName": "Wi-Fi Connection Configuration",
            "description": "It will configure wi-fi connection settings on",
            "category": "auto",
            "stepGroups": [
              {
                "steps": [
                  "Open Settings and tap Connections, then select Wi-Fi.",
                  "Tap the gear icon next to your network and select Forget Network, then reconnect."
                ],
                "actionableDeeplink": {
                  "deeplink": "bixby://com.samsung.android.settings.connections.wifi",
                  "description": "It will manage wireless network connections",
                  "message": "Wi-Fi Settings"
                },
                "validationDeeplink": {
                  "deeplink": "bixby://com.samsung.android.settings.connections.wifi",
                  "key": "wifi_enabled",
                  "resultType": "boolean",
                  "condition": "equal",
                  "value": "true"
                }
              }
            ]
          },
          {
            "actionName": "Wi-Fi Connection Recovery",
            "description": "It will perform device recovery and reboot",
            "category": "manual",
            "stepGroups": [
              {
                "steps": ["If drops continue, restart your Wi-Fi router."]
              }
            ]
          },
          {
            "actionName": "Reset Network Settings",
            "description": "It will guide your manual hardware inspection",
            "category": "critical",
            "stepGroups": [
              {
                "steps": ["Navigate to General Management, tap Reset, and choose Reset Network Settings."],
                "actionableDeeplink": {
                  "deeplink": "bixby://com.samsung.android.settings.general.reset_network",
                  "description": "It will reset wireless network configurations",
                  "message": "Reset Network Settings"
                }
              }
            ]
          }
        ]
      }
    ]
  },
  "meta": {
    "latency_ms": 12,
    "cache_hit": true,
    "model": "openai/gpt-oss-20b",
    "cost_usd": 0.0
  }
}
```

### 2. Reset Semantic Cache
```bash
curl -X DELETE http://127.0.0.1:8000/v1/cache
```

---

## 🏗️ System Architecture

Complete architectural diagrams, component interactions, and data schemas are detailed in [ARCHITECTURE.md](ARCHITECTURE.md).

```text
[ Client: One UI Web App / REST API ]
                 │
                 ▼
[ Gateway: FastAPI 0.110 + Pydantic Contract Inbound Validator ]
                 │
                 ├───────────► [ Multi-Tier Semantic Cache (Sub-2ms Hit) ]
                 │
                 ▼ (Cache Miss)
[ Multi-Intent & Hybrid Semantic Matcher (ChromaDB Vector + BM25 Lexical) ]
                 │
                 ▼
[ AI Extraction Engine (Groq Llama 3 / gpt-oss-20b + Zero-Fail Fallback) ]
                 │
                 ▼
[ Bixby Deeplink Resolver + Precondition Invalidator ]
                 │
                 ▼
[ Strict Gatekeeper: Gate G5 Zero-URL Scrubber & Block A1-A5 Sanitizer ]
                 │
                 ▼
[ Final Response Envelope with Observability Metadata ]
```

---

## 📊 Evaluation & Benchmarks

Full benchmark methodology and logs are provided in [metrics.md](metrics.md).

| Evaluation Gate / Scoring Block | Requirement | Result | Status |
|---|---|---|:---:|
| **Gate G2** | Unauthenticated `GET /health` returns `{"status": "ok"}` | Status 200, `{"status": "ok"}` | **PASS** |
| **Gate G3** | Coverage of 20 benchmark test scenarios | **100.0%** (20 / 20 scenarios in `results.jsonl`) | **PASS** |
| **Gate G4** | Schema compliance against PRISM Appendix A | **100.0%** valid Pydantic responses | **PASS** |
| **Gate G5** | Zero external URL / hyperlink leaks | **0 leaks** detected across all tests | **PASS** |
| **Latency (Cold Start)** | First call latency P95 &le; 8,000 ms | **4,279.3 ms** | **PASS** |
| **Latency (Cache Hit)** | Repeat call latency P95 &le; 300 ms | **0.8 ms** (P50), **1.7 ms** (P95) | **PASS** |
| **Cache Hit Rate** | Repeat queries &ge; 90% hit rate | **100.0%** hit rate | **PASS** |
| **Semantic Hit Rate** | Paraphrased queries &ge; 80% hit rate | **100.0%** hit rate | **PASS** |
| **Block A1 Rules** | Strict Goal syntax, 2–3 word titles, 5–7 word "It will..." desc | **100.0%** deterministic compliance | **PASS** |
| **Block A2 Rules** | Priority sorting: `auto` &rarr; `manual` &rarr; `critical` | Enforced deterministically | **PASS** |
| **Block A5 Rules** | Strictly 8 to 10 unique query variations | Enforced deterministically | **PASS** |

### Run the Benchmark Suite Yourself:
```bash
python benchmark.py
```

### Regenerate the 20-Scenario Submission File:
```bash
python results_generator.py
```

---

## 📋 Hackathon Submission Checklist

As required by the Samsung PRISM submission guidelines:

- [x] **Source Code:** Complete modular backend (`app/`), knowledge catalog (`data/`), validator (`validator.py`), and One UI web client (`ui/index.html`).
- [x] **README:** Comprehensive, professional, clean guide with requirements, setup, and usage examples.
- [x] **Runbook:** Step-by-step cross-platform guide in [RUNBOOK.md](RUNBOOK.md).
- [x] **Architecture Document:** Technical specifications, Mermaid diagrams, and tool stack in [ARCHITECTURE.md](ARCHITECTURE.md).
- [x] **Metrics Report:** Complete benchmark measurements in [metrics.md](metrics.md).
- [x] **Presentation:** Presentation deck prepared for submission.
- [x] **Video:** Demonstration video showing live multi-intent query, tri-category sorting, follow-up buttons, and sub-millisecond cache hits.
- [x] **AI Disclosure:** Disclosed below in accordance with PRISM hackathon guidelines.
- [x] **Submission Tag:** Tagged as `PRISM_GENAI_HACKATHON_Y2026`.

---

## 🤖 AI Disclosure

In accordance with Samsung PRISM hackathon guidelines:
- **LLM Services Used:** Groq LPU API running `openai/gpt-oss-20b` and Llama 3 for step extraction, action summarization, and query paraphrasing.
- **Local Neural Embeddings:** `sentence-transformers` utilizing the open-source `all-MiniLM-L6-v2` model for dense vector search and semantic cache cosine similarity.
- **Algorithmic Fallbacks:** Deterministic rule-based extraction and BM25 indexing developed in Python to guarantee 100% availability and contract compliance during cloud rate-limits.
- **Human Authorship:** System architecture, multi-tier semantic cache design, One UI design system implementation, contract validation algorithms, and benchmarking suite were engineered and verified by the team.

---

## 📄 License & Authors

Distributed under the **MIT License**. See `LICENSE` for more information.

- **Project:** PRISM Smart Guided Troubleshooting Engine
- **Hackathon:** Samsung PRISM Hackathon 2026 — Theme 2
- **Submission Tag:** `PRISM_GENAI_HACKATHON_Y2026`
