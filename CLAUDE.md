# CLAUDE.md — ChemBrain

Autonomous AI operations agent for an industrial chemical plant. Monitors real-time
sensor data, detects anomalies, and autonomously adjusts plant controls to minimise
operating cost while maintaining safety margins. Every decision is spoken aloud to
operators via ElevenLabs.

---

## Architecture

```
Sensor data (CSV replay)
        │
        ▼
┌─────────────────────┐
│   Monitor Agent     │  Watches all sensors each tick.
│   agent_monitor.py  │  Three checks: threshold breach,
│                     │  linear trend, rate-of-change spike.
└──────────┬──────────┘
           │  Alert dicts
           ▼
┌─────────────────────┐
│  Supervisor Agent   │  OpenAI (gpt-5.5) with tool-calling.
│  agent_supervisor.py│  Reasons over plant state, picks lowest-cost
│                     │  safe action. Re-reasons if Control rejects.
└──────┬──────────┬───┘
       │          │
       ▼          ▼
┌──────────┐  ┌─────────────┐
│ Control  │  │ Voice Agent │
│ Agent    │  │ agent_voice │
│          │  │             │
│ Validates│  │ ElevenLabs  │
│ against  │  │ TTS → speaks│
│ safety   │  │ decision to │
│ envelope │  │ operator    │
└──────────┘  └─────────────┘
```

---

## Project structure

```
├── api.py                  ← FastAPI backend + WebSocket
├── pipeline.py             ← wires agents together per tick
├── requirements.txt
│
├── agents/
│   ├── agent_monitor.py    ← anomaly detection (3 methods)
│   ├── agent_supervisor.py ← OpenAI tool-calling orchestrator
│   ├── agent_control.py    ← validates + executes control actions
│   └── agent_voice.py      ← ElevenLabs TTS, pyttsx3 fallback
│
├── plant/
│   ├── loader.py           ← reads CSVs from Base Dataset/
│   ├── simulator.py        ← tick-based state machine
│   ├── safety_envelope.py  ← hard limits + action rate limits
│   └── cost_model.py       ← energy_consumption → £/hr
│
├── config/
│   ├── plant_config.py     ← zone names, sensor units, normal ranges
│   └── thresholds.py       ← alert thresholds, spike/trend config
│
├── Base Dataset/
│   ├── plant_hierarchy.csv ← 5 zones (R-101, R-102, HX-01, C-01, Util)
│   └── plant_metrics.csv   ← 7 days hourly sensor data, 4 anomaly scenarios
│
└── frontend/               ← React + Vite
    └── src/
        ├── App.jsx / App.css
        ├── hooks/usePlantData.js   ← WebSocket hook with auto-reconnect
        └── components/
            ├── SensorPanel.jsx     ← zone cards, colour-coded sensor rows
            ├── ActivityLog.jsx     ← decision feed, alert banners, voice quotes
            └── ControlPanel.jsx    ← setpoints, override toggle, emergency stop
```

---

## Sensors

| Sensor              | Unit  | Normal range | Alert (warn / crit)  |
|---------------------|-------|--------------|----------------------|
| temperature         | °C    | 160 – 200    | >220 / >240          |
| pressure            | bar   | 3.0 – 5.5    | >6.5 / >8.0          |
| co2                 | ppm   | 250 – 480    | >680 / >900          |
| flow_rate           | L/min | 85 – 110     | <50 / <30            |
| ph                  | pH    | 6.9 – 7.4    | <6.1 / <5.5          |
| energy_consumption  | kW    | 180 – 230    | >300 / >380          |

(Values shown for R-101. Each zone has its own thresholds in `config/thresholds.py`.)

---

## Embedded anomaly scenarios (plant_metrics.csv)

| Hour    | Zone  | Sensor      | Type    | Peak     | Recovery |
|---------|-------|-------------|---------|----------|----------|
| 34 – 60 | R-101 | temperature | trend   | 243 °C   | h50–60   |
| 110–120 | R-102 | co2         | spike   | 925 ppm  | h113–120 |
| 130–158 | R-101 | ph          | trend   | pH 5.6   | h148–158 |
| 155–167 | HX-01 | flow_rate   | spike   | 27 L/min | h162–167 |

Each anomaly has a scripted recovery to show the agent closing the loop.

---

## Control actions

| Action                      | Max delta/call | Primary sensor affected |
|-----------------------------|----------------|-------------------------|
| adjust_heater_power         | ±20%           | energy_consumption      |
| adjust_feed_rate            | ±15%           | flow_rate               |
| adjust_vent_valve           | ±25%           | co2                     |
| adjust_temperature_setpoint | ±5 °C          | temperature             |

If Control rejects an action (safety envelope breach), Supervisor re-reasons
with the rejection reason and safe_max included in context.

---

## How to run

```bash
# Python setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd frontend && npm run dev
```

Open `http://localhost:5173`.

### Environment variables

```
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=Rachel   # optional
```
