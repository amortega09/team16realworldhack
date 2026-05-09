import os
import json
from openai import OpenAI
from plant.cost_model import compute_cost_per_hour, project_cost_after_action
from config.plant_config import ZONES, SENSOR_UNITS

MODEL = "gpt-5.5"

SYSTEM_PROMPT = """You are ChemBrain, the autonomous operations supervisor for an industrial chemical plant.

Your job is to monitor sensor alerts and take the lowest-cost safe corrective action.

Rules you must never break:
1. Safety is absolute. Never propose an action that would push a sensor outside its hard limits.
2. If the Control Agent rejects your action, re-reason with the stated constraint and try again with a smaller delta.
3. Always prefer the action that resolves the alert at lowest energy cost.
4. After deciding on an action, call dispatch_voice with a clear operator briefing — spoken in plain English, as if calling a human operator on the phone. Include: what the problem is, how serious it is, what you are doing about it, and the estimated cost impact.
5. Always call log_decision last to record your reasoning.

Available control actions:
- adjust_heater_power: change heater output (delta in % of rated, negative = reduce)
- adjust_feed_rate: change feedstock flow (delta in % of nominal, negative = reduce)
- adjust_vent_valve: change vent opening (delta in % open, positive = open more)
- adjust_temperature_setpoint: shift reactor temperature target (delta in °C)

The voice message will be spoken aloud to the plant operator immediately. Make it sound like a professional automated call, not a system log."""

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
            "name": "get_cost_projection",
            "description": "Get the current operating cost and projected cost after a proposed action.",
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

    def handle(self, alerts: list[dict], state: dict) -> dict | None:
        if not alerts:
            return None

        messages = [
            {"role": "system",  "content": SYSTEM_PROMPT},
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

        elif name == "get_cost_projection":
            current_cost   = compute_cost_per_hour(state)
            projected_cost = project_cost_after_action(
                state, inputs["zone"], inputs["action"], inputs["delta"]
            )
            return {
                "current_cost_gbp_per_hr":   current_cost,
                "projected_cost_gbp_per_hr": projected_cost,
                "saving_gbp_per_hr":         round(current_cost - projected_cost, 2),
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
            self._voice.speak(inputs["message"])
            return {"status": "speaking"}

        elif name == "log_decision":
            decision["reasoning"]    = inputs.get("reasoning", decision["reasoning"])
            decision["action_taken"] = inputs.get("action_taken", decision["action_taken"])
            decision["cost_impact"]  = inputs.get("cost_impact_gbp_per_hr", decision["cost_impact"])
            return {"status": "logged"}

        return {"error": f"Unknown tool: {name}"}

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
