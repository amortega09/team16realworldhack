import os
import json
from openai import OpenAI
from plant.cost_model import compute_cost_per_hour, project_cost_after_action
from plant.objective_model import compute_objective_metrics, project_objectives_after_action
from config.plant_config import SENSOR_NORMAL_RANGES, SENSOR_UNITS

MODEL = "gpt-5.5"

SYSTEM_PROMPT = """You are ChemBrain, the autonomous operations supervisor for an industrial chemical plant.

Your job is to monitor sensor alerts and take the safest corrective action while balancing the live optimisation goals provided below.

Rules you must never break:
1. Safety is absolute. Never propose an action that would push a sensor outside its hard limits.
2. If the Control Agent rejects your action, re-reason with the stated constraint and try again with a smaller delta.
3. Respect the current optimisation weights and target conditions when selecting between safe actions.
4. Use get_action_projection to compare candidate actions against the active objective set when tradeoffs are meaningful.
5. After deciding on an action, call dispatch_voice with a clear operator briefing in plain English. The backend may mute audible playback, but you should still generate the operator briefing text.
6. Always call log_decision last to record your reasoning.

Available control actions:
- adjust_heater_power: change heater output (delta in % of rated, negative = reduce)
- adjust_feed_rate: change feedstock flow (delta in % of nominal, negative = reduce)
- adjust_vent_valve: change vent opening (delta in % open, positive = open more)
- adjust_temperature_setpoint: shift reactor temperature target (delta in °C)

Make tradeoffs deliberately. If weights emphasize safety or stability, prefer more conservative actions. If they emphasize cost or throughput, improve those outcomes without violating safety."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_plant_state",
            "description": "Get current sensor readings for all zones in the plant.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_action_projection",
            "description": "Get current and projected operating metrics after a proposed action, including cost and optimization objectives.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone":   {"type": "string", "description": "Zone identifier e.g. r101"},
                    "action": {"type": "string"},
                    "delta":  {"type": "number"},
                },
                "required": ["zone", "action", "delta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dispatch_control",
            "description": "Send a control action to the Control Agent for execution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone":   {"type": "string"},
                    "action": {
                        "type": "string",
                        "enum": ["adjust_heater_power", "adjust_feed_rate",
                                 "adjust_vent_valve", "adjust_temperature_setpoint"],
                    },
                    "delta":  {"type": "number", "description": "Magnitude of adjustment. Negative = reduce."},
                    "reason": {"type": "string", "description": "One-sentence rationale."},
                },
                "required": ["zone", "action", "delta", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dispatch_voice",
            "description": "Speak an operator briefing aloud via ElevenLabs. Call this after dispatching control.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": (
                            "Plain English spoken message for the operator. "
                            "Should explain: what triggered the alert, the severity, "
                            "what action was taken, and the cost impact. "
                            "Speak as if calling the operator on the phone."
                        ),
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_decision",
            "description": "Record the final decision. Always call this last.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning":              {"type": "string"},
                    "action_taken":           {"type": "string"},
                    "cost_impact_gbp_per_hr": {"type": "number"},
                },
                "required": ["reasoning", "action_taken", "cost_impact_gbp_per_hr"],
            },
        },
    },
]


class SupervisorAgent:
    def __init__(self, simulator, control_agent, voice_agent):
        self._sim     = simulator
        self._control = control_agent
        self._voice   = voice_agent
        self._client  = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._optimization_settings = self._build_default_optimization_settings()

    def handle(self, alerts: list[dict], state: dict) -> dict | None:
        if not alerts:
            return None

        messages = [
            {"role": "system",  "content": self._build_system_prompt()},
            {"role": "user",    "content": self._format_alerts(alerts, state)},
        ]

        decision = {
            "alerts":         alerts,
            "control_result": None,
            "voice_message":  None,
            "reasoning":      "",
            "action_taken":   "none",
            "cost_impact":    0.0,
        }

        for _ in range(10):  # safety cap on iterations
            response = self._client.chat.completions.create(
                model=MODEL,
                tools=TOOLS,
                messages=messages,
            )

            msg = response.choices[0].message

            if msg.content:
                decision["reasoning"] += msg.content + "\n"

            # No tool calls — model is done
            if not msg.tool_calls:
                break

            # Append assistant turn
            messages.append(msg)

            # Execute each tool call and append results
            for tc in msg.tool_calls:
                args   = json.loads(tc.function.arguments)
                result = self._execute_tool(tc.function.name, args, state, decision)
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      json.dumps(result, default=str),
                })

        return decision

    def _execute_tool(self, name: str, inputs: dict, state: dict, decision: dict) -> dict:
        if name == "get_plant_state":
            return {
                zone: {
                    "display_name": data["display_name"],
                    "sensors": {
                        f"{s} ({SENSOR_UNITS.get(s, '')})": round(v, 2)
                        for s, v in data["sensors"].items()
                    },
                    "is_working": data["is_working"],
                }
                for zone, data in state.items()
            }

        elif name == "get_action_projection":
            current_cost = compute_cost_per_hour(state)
            current_objectives = compute_objective_metrics(state)
            projected_cost = project_cost_after_action(
                state, inputs["zone"], inputs["action"], inputs["delta"]
            )
            projected_objectives = project_objectives_after_action(
                state,
                inputs["zone"],
                inputs["action"],
                inputs["delta"],
                previous_state=state,
            )
            return {
                "current_cost_gbp_per_hr": current_cost,
                "projected_cost_gbp_per_hr": projected_cost,
                "saving_gbp_per_hr": round(current_cost - projected_cost, 2),
                "current_objectives": current_objectives,
                "projected_objectives": projected_objectives,
            }

        elif name == "dispatch_control":
            result = self._control.execute(
                zone=inputs["zone"],
                action=inputs["action"],
                delta=inputs["delta"],
                reason=inputs["reason"],
            )
            decision["control_result"] = result
            if result["status"] == "executed":
                decision["action_taken"] = f"{inputs['action']} on {inputs['zone']} by {inputs['delta']:+.1f}"
                decision["cost_impact"]  = result.get("saving", 0.0)
            return result

        elif name == "dispatch_voice":
            decision["voice_message"] = inputs["message"]
            return self._voice.speak(inputs["message"])

        elif name == "log_decision":
            decision["reasoning"]    = inputs.get("reasoning", decision["reasoning"])
            decision["action_taken"] = inputs.get("action_taken", decision["action_taken"])
            decision["cost_impact"]  = inputs.get("cost_impact_gbp_per_hr", decision["cost_impact"])
            return {"status": "logged"}

        return {"error": f"Unknown tool: {name}"}

    def update_optimization_settings(self, updates: dict | None) -> dict:
        if not updates:
            return self.get_optimization_settings()

        weights = updates.get("weights")
        if isinstance(weights, dict):
            for key, raw_value in weights.items():
                if not isinstance(key, str):
                    continue
                normalized_key = self._normalize_metric_key(key)
                if not normalized_key:
                    continue
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    continue
                self._optimization_settings["weights"][normalized_key] = max(0.0, min(10.0, value))

        objectives = updates.get("objectives")
        if isinstance(objectives, dict):
            for key, raw_description in objectives.items():
                if not isinstance(key, str):
                    continue
                normalized_key = self._normalize_metric_key(key)
                if not normalized_key:
                    continue
                if isinstance(raw_description, str):
                    description = raw_description.strip()
                    if description:
                        self._optimization_settings["objectives"][normalized_key] = description
                self._optimization_settings["weights"].setdefault(normalized_key, 5.0)

        targets = updates.get("targets")
        if isinstance(targets, dict):
            for sensor, current in self._optimization_settings["targets"].items():
                if sensor in targets:
                    raw = targets[sensor]
                    if raw in ("", None):
                        self._optimization_settings["targets"][sensor] = None
                        continue
                    try:
                        self._optimization_settings["targets"][sensor] = round(float(raw), 3)
                    except (TypeError, ValueError):
                        self._optimization_settings["targets"][sensor] = current

        summary = updates.get("summary")
        if isinstance(summary, str):
            self._optimization_settings["summary"] = summary.strip() or self._optimization_settings["summary"]

        return self.get_optimization_settings()

    def get_optimization_settings(self) -> dict:
        return {
            "summary": self._optimization_settings["summary"],
            "weights": dict(self._optimization_settings["weights"]),
            "objectives": dict(self._optimization_settings["objectives"]),
            "targets": dict(self._optimization_settings["targets"]),
        }

    def _build_system_prompt(self) -> str:
        settings = self.get_optimization_settings()
        weights = settings["weights"]
        targets = settings["targets"]
        lines = [
            SYSTEM_PROMPT,
            "",
            "Current optimisation summary:",
            settings["summary"],
            "",
            "Current optimisation objectives and weights (0-10):",
        ]

        for key, weight in weights.items():
            description = settings["objectives"].get(key, "Custom optimisation objective.")
            lines.append(f"- {key}: weight {weight} — {description}")

        lines.extend([
            "",
            "Use higher-weight objectives as stronger decision priorities when tradeoffs are needed.",
            "",
            "Target sensor conditions to steer toward when practical:",
        ])

        for sensor, value in targets.items():
            unit = SENSOR_UNITS.get(sensor, "")
            if value is None:
                lines.append(f"- {sensor}: no explicit target")
            else:
                lines.append(f"- {sensor}: target {value} {unit}".rstrip())

        return "\n".join(lines)

    @staticmethod
    def _format_alerts(alerts: list[dict], state: dict) -> str:
        lines = ["PLANT ALERT — autonomous action required.\n"]
        for a in alerts:
            zone_name = state.get(a['zone'], {}).get('display_name', a['zone'])
            units     = SENSOR_UNITS.get(a['sensor'], '')
            line = (
                f"• [{a['severity'].upper()}] {zone_name} — {a['sensor']}: "
                f"{a['value']} {units} ({a['type']} alert, threshold {a['threshold']} {units})"
            )
            if a.get('minutes_to_breach'):
                line += f", predicted breach in {a['minutes_to_breach']} min"
            if a.get('trend_slope'):
                line += f", trend: {a['trend_slope']:+.2f} {units}/hr"
            lines.append(line)
        lines.append("\nAssess the situation, take the safest lowest-cost corrective action, brief the operator, and log your decision.")
        return "\n".join(lines)

    @staticmethod
    def _build_default_optimization_settings() -> dict:
        sensor_samples: dict[str, list[float]] = {}
        for zone_ranges in SENSOR_NORMAL_RANGES.values():
            for sensor, bounds in zone_ranges.items():
                midpoint = round((bounds[0] + bounds[1]) / 2, 3)
                sensor_samples.setdefault(sensor, []).append(midpoint)

        targets = {
            sensor: round(sum(values) / len(values), 3)
            for sensor, values in sensor_samples.items()
        }

        return {
            "summary": "Prioritise safe, stable operation first, then reduce energy cost while keeping the plant near nominal targets.",
            "weights": {
                "safety_margin": 10.0,
                "operating_cost": 7.0,
                "stability": 8.0,
                "throughput": 5.0,
                "co2_emissions": 6.0,
                "product_quality": 7.0,
                "equipment_wear": 5.0,
                "recovery_time": 6.0,
            },
            "objectives": {
                "safety_margin": "Keep strong distance from hard safety limits and avoid risk escalation.",
                "operating_cost": "Reduce hourly operating cost where it does not compromise safety.",
                "stability": "Avoid oscillations, abrupt swings, and unstable process behavior.",
                "throughput": "Preserve useful production flow and avoid unnecessary output loss.",
                "co2_emissions": "Reduce CO2-heavy operating choices and avoid unnecessary venting or emissions growth.",
                "product_quality": "Keep process conditions close to nominal quality-friendly ranges.",
                "equipment_wear": "Avoid aggressive or frequent actuator changes that increase wear.",
                "recovery_time": "Return the plant to normal operation quickly after disturbances.",
            },
            "targets": targets,
        }

    @staticmethod
    def _normalize_metric_key(value: str) -> str:
        cleaned = value.strip().lower().replace(" ", "_").replace("-", "_")
        cleaned = "".join(char for char in cleaned if char.isalnum() or char == "_")
        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")
        return cleaned.strip("_")
