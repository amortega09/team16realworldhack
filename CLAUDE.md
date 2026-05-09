# CLAUDE.md — ChemBrain

Autonomous AI operations agent for an industrial chemical plant. Monitors real-time
sensor data, detects anomalies, and autonomously adjusts plant controls to minimise
operating cost while maintaining safety margins. Voice announcements, optimisation
priorities, target operating conditions, and speech-to-text input can all be
changed live at runtime.

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
│  agent_supervisor.py│  Reasons over plant state, balances live
│                     │  optimisation goals, uses projected objective metrics,
│                     │  re-reasons if Control rejects.
└──────┬──────────┬───┘
       │          │
       ▼          ▼
┌──────────┐  ┌─────────────┐
│ Control  │  │ Voice Agent │
│ Agent    │  │ agent_voice │
│          │  │             │
│ Validates│  │ ElevenLabs  │
│ against  │  │ / pyttsx3   │
│ safety   │  │ queued TTS, │
│ envelope │  │ STT + no overlap
└──────────┘  └─────────────┘

Additional backend utility agent:

┌─────────────────────┐
│    Read Agent       │  LangGraph + LangChain repo inspector.
│    agent_read.py    │  Reads `CLAUDE.md`, backend files, and
│                     │  other repository text files via safe tools.
└─────────────────────┘
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
│   ├── agent_read.py       ← LangGraph/LangChain repo-reading agent
│   ├── agent_supervisor.py ← OpenAI tool-calling orchestrator + live optimisation
│   ├── agent_control.py    ← validates + executes control actions
│   └── agent_voice.py      ← runtime-controlled queued voice + ElevenLabs STT
│
├── plant/
│   ├── loader.py           ← reads CSVs from Base Dataset/
│   ├── simulator.py        ← tick-based state machine
│   ├── safety_envelope.py  ← hard limits + action rate limits
│   ├── cost_model.py       ← energy_consumption → £/hr
│   └── objective_model.py  ← projected optimisation metrics for agent reasoning
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
            └── ControlPanel.jsx    ← setpoints, voice/STT, optimisation editor
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

## Runtime controls

The backend now supports live runtime configuration without restarting the app.

### Voice controls

- Speech can be enabled or muted in real time.
- Voice playback is queued so multiple announcements never overlap.
- Voice ID can be changed at runtime.
- The supervisor still generates operator briefing text even if audible speech is muted.

### Optimisation controls

The supervisor uses live optimisation settings on each decision tick:

- Strategy summary: free-text description of what the agent should prioritise
- Weights: built-in objectives plus custom user-defined objectives
- Target conditions: editable target values for the main plant sensors

These settings can be changed while the simulation is running, and the next
supervisor decision will use the updated values.

### Objective model

The backend now provides deterministic projected metrics so the supervisor can
reason over more than just cost. Current computed/projected objectives include:

- `co2_emissions`
- `throughput`
- `product_quality`
- `equipment_wear`
- `stability`
- `maintenance_risk`
- `recovery_time`
- `alarm_load`
- `utility_efficiency`
- `flaring_or_venting`

The control panel can also define additional custom objective names and weights.
Those custom objectives are included in the supervisor prompt immediately.

### Speech to text

- The control panel includes a microphone recording button.
- Recorded browser audio is uploaded to the backend.
- The backend sends that audio to ElevenLabs Scribe v2 for transcription.
- The resulting transcript is returned to the UI.

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

### Read agent endpoint

The backend also exposes a repo-inspection endpoint for development workflows:

```bash
POST /api/agents/read
{
  "query": "Read CLAUDE.md and summarize the backend agents."
}
```

### Runtime settings endpoint

The backend also exposes a live settings endpoint:

```bash
POST /api/settings
{
  "voice": {
    "enabled": true,
    "voice_id": "Rachel"
  },
  "optimization": {
    "summary": "Prioritise safety first, then stability, then energy cost.",
    "weights": {
      "safety_margin": 10,
      "co2_emissions": 8,
      "operating_cost": 6,
      "stability": 9,
      "throughput": 4
    },
    "objectives": {
      "co2_emissions": "Reduce emissions during control actions.",
      "equipment_wear": "Avoid aggressive or frequent actuator changes."
    },
    "targets": {
      "temperature": 140,
      "pressure": 3.5,
      "co2": 320
    }
  }
}
```

### Speech-to-text endpoint

The backend also exposes an upload-based transcription endpoint:

```bash
POST /api/transcribe
multipart/form-data

audio=<recorded audio blob>
language_code=eng   # optional
```
