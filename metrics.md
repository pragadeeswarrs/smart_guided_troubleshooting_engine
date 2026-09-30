# PRISM Benchmark Performance & Quality Report

**Generated Date:** 2026-09-30  
**Evaluator:** Automated Verification Suite (`benchmark.py` & `validator.py`)  
**Theme:** Samsung PRISM Hackathon - Theme 2: Smart Guided Troubleshooting Engine  
**Associated Docs:** [RUNBOOK.md](RUNBOOK.md) | [ARCHITECTURE.md](ARCHITECTURE.md) | [README.md](README.md)

---

## 1. Executive Summary: Scoring Gates (Must-Pass)

| Gate | Requirement | Measured Result | Status |
|---|---|---|:---:|
| **Gate G2** | `GET /health` returns `{"status": "ok"}` without auth | Status 200, `{"status": "ok"}` | **PASS** |
| **Gate G3** | At least 95% of test queries covered in `results.jsonl` | **100.0%** (20 / 20 scenarios) | **PASS** |
| **Gate G4** | At least 90% of responses pass strict Pydantic `schemas.py` | **100.0%** schema validity | **PASS** |
| **Gate G5** | ZERO URL leaks (`http`, `https`, `www`, `.com`, `.html`) | **0 leaks** across all responses | **PASS** |

---

## 2. Latency & Caching Benchmarks

| Benchmark Metric | Target Threshold | Measured P50 | Measured P95 | Status |
|---|---|---|---|:---:|
| **Cold Start Latency** | P95 <= 8000 ms | - | **4279.3 ms** | **PASS** |
| **Repeat Query Latency** (30x) | P95 <= 300 ms | **0.8 ms** | **1.7 ms** | **PASS** |
| **Repeat Cache Hit Rate** | >= 90% | - | **100.0%** | **PASS** |
| **Paraphrase Semantic Hit Rate** (20x) | >= 80% | - | **100.0%** | **PASS** |

---

## 3. Structural & Formatting Compliance (Blocks A1 - A5)

| Scoring Block | Automated Grading Criterion | Rule Enforcement | Status |
|---|---|---|:---:|
| **Block A1** | Goal Regex Format | `Follow these steps to perform this <Name> Troubleshooting.` | **PASS** |
| **Block A1** | Title Word Count | Strictly 2 to 3 words (Title Case) | **PASS** |
| **Block A1** | Action Description | Strictly 5 to 7 words, starting with `"It will"` | **PASS** |
| **Block A1** | Score Range | Clamped float between 0.0 and 1.0 | **PASS** |
| **Block A2** | Category Sorting | Actions strictly sorted auto -> manual -> critical | **PASS** |
| **Block A2** | Auto Deeplink Fallback | Unmatched auto actions fallback to `bixby://dummy_positive` | **PASS** |
| **Block A5** | Query Variations | Strictly 8 to 10 unique variations per scenario | **PASS** |

---

## 4. Multi-Intent & Composite Query Evaluation

| Composite Query Test | Detected Scenarios | Category Coverage | Deeplink Resolution |
|---|---|:---:|---|
| `"My Wi-Fi keeps disconnecting, router restart didn't help, and battery is draining fast"` | Scenario 2 (Battery) + Scenario 3 (Wi-Fi) | `auto`, `manual`, `critical` | `Power Saving`, `Wi-Fi Settings`, `Reset Network Settings` |
| `"Phone is overheating while charging, cable gets hot, and Wi-Fi disconnects continuously"` | Scenario 6 (Overheating) + Scenario 3 (Wi-Fi) | `auto`, `manual`, `critical` | `Power Saving`, `Wi-Fi Settings`, `Reset Network Settings` |
| `"Wi-Fi connection keeps dropping randomly, router isn't fixing it, and device storage is full"` | Scenario 3 (Wi-Fi) + Scenario 13 (Storage) | `auto`, `manual`, `critical` | `Wi-Fi Settings`, `Internal Storage`, `Reset Network Settings` |

---

## 5. Gate G5 URL Leak Audit Log

- **Audit Target:** `results.jsonl` + Live endpoint `/v1/troubleshoot` responses
- **Regex Patterns Checked:** `https?://\S+`, `www\.\S+`, `\.(com|html|org|net)\S*`, `\[.*?\]\(.*?\)`, `<a href=...>`
- **Total Violations Detected:** **0**
- **Conclusion:** 100% compliant with Gate G5 zero-leak policy.
