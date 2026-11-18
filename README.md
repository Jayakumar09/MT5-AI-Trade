# QUANT PILOT

**Multi-agent AI trading desk by JAYAKUMAR.ai** — trades a **Liquidity Sweep (stop-hunt reversal)** strategy on **XAUUSD** and **BTCUSD** using seven cooperating AI agents, with a unique, professional, highly animated 2D/3D interface.

> **Educational use only. Not financial advice. Trading involves risk of loss.**

## Status

- Backend: FastAPI + WebSocket streaming (port **8000**) — verified: `GET /health` → ok, full agent cycle runs, outcome `TAKEN`
- Frontend: Vite + React + TypeScript + Tailwind + R3F (port **5173**) — builds cleanly (`npm run build`)
- Demo Mode is **default** — no broker, no API key required
- Unit tests: **25 passed** (sweep detector, risk calculations, Analyst JSON schema)

## 3-command setup

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
python run.py
```

`python run.py` copies `.env.example` → `.env` (Demo Mode ON) the first time, starts the FastAPI backend on **:8000** and the Vite dev server on **:5173**, and opens the browser.

- App: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Demo → MT5 switch

1. Install and log in to a MetaTrader 5 terminal (Windows).
2. In `.env`, set:
   ```
   ENABLE_MT5=true
   MT5_MODE=demo_only        # or "live" — live also requires the typed confirmation in Settings
   MT5_LOGIN=<account>
   MT5_PASSWORD=<password>
   MT5_SERVER=MetaQuotes-Demo
   MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
   MT5_MAGIC=16112026
   ```
3. Restart with `python run.py`. If MT5 is unavailable the app falls back to Demo automatically and shows a banner.
4. **Live mode** additionally requires typing `I ACCEPT THE RISK` in Settings → Guardrails. Paper/Demo remains the default; the Risk Guardian always has the final veto (LLM output never reaches execution without AEGIS approval).

## Claude API key (optional)

Without a key the Analyst uses a deterministic rule-based mock (Demo-friendly). With a key:

```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-5-5
```

The Analyst returns **strict JSON** validated by Pydantic (`AnalysisDecision`), retries once on invalid output, then returns `NO_TRADE`. Claude may only **refine or reject** the Hunter's candidate — never invent prices.

## The seven agents

| # | Agent | Role |
|---|-------|------|
| 1 | **Scout** | Data — OHLCV (5M/15M/4H/1D), spread, account info (MT5 or Demo) |
| 2 | **Cartographer** | Liquidity mapper — PDH/PDL, Asian/London/NY sessions, swings, equal highs/lows |
| 3 | **Hunter** | Sweep detector — sweep + displacement rule engine, exact candidate numbers |
| 4 | **Analyst** | Claude LLM — bias, confidence 1–10, strict JSON → Pydantic |
| 5 | **Risk Guardian** | AEGIS — hard-coded vetoes, lot sizing, min RR 1:2, min confidence 7, 4% daily DD kill |
| 6 | **Executioner** | Orders — paper engine by default; MT5 bridge (demo/live) with validation + idempotency |
| 7 | **Chronicler** | Journal — SQLite decision log with full trace + AI end-of-day review |

Each agent: `run(context) -> AgentResult(status, summary, data, confidence, timestamp)`. Orchestrator runs them in sequence every cycle (default: each 5M candle close) and broadcasts events over `/ws/events`.

## Strategy — Liquidity Sweep

- **Level known liquidity**: PDH/PDL, Asian session H/L, 4H swing H/L, equal highs/lows
- **Sweep depth**: XAUUSD 10–25 pips beyond the level; BTCUSD 0.15%–0.4%
- **Displacement**: closes back inside within 3 candles, body ≥ 1.2× average body
- **Entry**: confirmation close (or pullback to 50% of the sweep wick)
- **SL**: beyond wick extreme + buffer (5 pips XAUUSD · 0.1% BTC)
- **TP1**: 1:2 RR at opposite range boundary · **TP2**: next liquidity pool (1:3+)
- BE at 1R, partial close 50% at TP1, trail remainder to TP2
- **Invalidation**: no re-entry inside the range within 3 candles; news-hour filter
- XAUUSD is session-aware (Asian/London/New York, shown IST + UTC); BTCUSD is 24/7 with session context

## Project structure

```
backend/
  main.py              # FastAPI + WS (/health, /api/*, /ws/events)
  strategy.py          # sweep detector + depth validation
  agents/              # base.py + scout, cartographer, hunter, analyst,
                       #   risk_guardian, executioner, chronicler
  core/                # models, db, demo_data, indicators, risk (AEGIS),
                       #   paper_engine, mt5_client, orchestrator, paths
frontend/
  src/
    scenes/            # BootScene (cinematic intro), ConstellationScene (3D orbs)
    components/        # Cursor, TopBar, CommandDock, CommandPalette, HeroPanel,
                       #   ChartPanel (Lightweight Charts), SweepVisualizer,
                       #   RiskShield + KillSwitch, SignalCard, JournalPanel,
                       #   BacktestLab, SettingsPanel, AgentPanel, IntroOverlay, …
    store/             # Zustand store
    api/               # REST + WS client (reconnect/backoff)
tests/                 # pytest: sweep detector, risk calcs, JSON schema (25 tests)
data/                  # SQLite at data/quantpilot.db (gitignored)
run.py                 # one-command launcher (backend :8000 + frontend :5173)
.env.example           # Demo Mode ON by default
```

## Unit tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
```

## How to extend

- **New agent**: add `backend/agents/<name>.py` subclassing `agents.base.Agent`, register it in the `AGENT_SEQUENCE` / orchestrator, add an orb in `frontend/src/scenes/ConstellationScene.tsx`.
- **New strategy**: add a detector in `backend/strategy.py` (or a new module), wire it into Hunter, and extend `tests/`.
- **New risk rule**: add a function in `backend/core/risk.py` and a regression test in `tests/test_risk.py` — AEGIS vetoes must remain hard-coded, never LLM-overridable.
- **New view**: add a tab in `CommandDock` + `App.tsx`.

## Safety

- Paper trading by default. Live requires an explicit toggle **and** typed confirmation phrase.
- LLM output never reaches execution without the Risk Guardian.
- No guaranteed profits. No withdrawals. Educational use only.

## GitHub backup

The spec asks to commit after successful build & testing to `Jayakumar09/MT5-AI-Trade`.
Commit/push is **not done automatically** because `QUANT PILOT.docx` (in this repo) contains a plaintext MT5 password — **rotate that credential**, remove it from the doc, and commit with:

```bash
git add backend frontend tests docs run.py README.md .env.example requirements*.txt pyproject.toml
git commit -m "QUANT PILOT v1.0 — multi-agent MT5 AI trading desk (Demo Mode)"
git push origin main
```

---

**QUANT PILOT** · by JAYAKUMAR.ai · Educational use only · Not financial advice
