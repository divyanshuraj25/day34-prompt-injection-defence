# Day 34 - Prompt Injection Attack Suite & Defences (Gemini)

Builds an assistant ("AcmeBot"), attacks it with **10 prompt-injection payloads** in 4 categories,
adds **3 defence layers**, and re-measures. Uses the **Gemini API** (google-genai SDK) instead of OpenAI.

## Setup
```bash
cd day34_prompt_injection
python -m venv venv && venv\Scripts\activate     # Windows  (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env                           # Mac/Linux: cp .env.example .env
# edit .env and paste your key:  GEMINI_API_KEY=...   (free key: https://aistudio.google.com/apikey)
python run_suite.py
```
Offline dry run (no key, simulated vulnerable model - only checks the pipeline): `set MOCK_LLM=1` then `python run_suite.py`.

API server: `uvicorn app:app --reload` -> open http://127.0.0.1:8000/docs

## Files
| File | Purpose |
|---|---|
| `system_prompt.py` | AcmeBot system prompt incl. a **canary** secret used to detect leaks |
| `attacks.py` | The 10 payloads (+1 extra), benign queries, moderation probes |
| `llm_client.py` | Gemini wrapper (+ offline mock) |
| `sanitizer.py` | **Layer 1** - input sanitisation (queries rejected; doc chunks stripped) |
| `output_validator.py` | **Layer 2** - output validation (prompt leak / persona change) |
| `moderation.py` | **Layer 3** - pre-call moderation (Gemini-based; harassment, self-harm, hate) |
| `pipeline.py` | `chat()` combining the layers (each can be toggled) |
| `classifier.py` | Labels each result INJECTED / PARTIAL / BLOCKED |
| `run_suite.py` | Runs before & after, prints raw responses, writes `results/results.md` + `.json` |
| `app.py` | FastAPI endpoints (`/chat`, `/attacks/run`) |
| `RESIDUAL_RISK.md` | Residual risk document (submission item) |

## Attack categories
1-3 direct role override | 4-6 instruction leakage | 7-9 jailbreak via fictional framing | 10 indirect injection via document chunk

## Note on moderation
OpenAI's `/moderations` endpoint needs an OpenAI key. With Gemini, the moderation layer asks Gemini (JSON mode)
to score `harassment`, `self_harm`, `hate`; anything >= `MODERATION_THRESHOLD` (default 0.5) is rejected
before the main LLM call. Fails closed by default.

## Results
Run `python run_suite.py` - the before/after table is saved to `results/results.md`. Paste it here / into your submission.
