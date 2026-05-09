from plant.simulator import PlantSimulator
from plant.cost_model import compute_cost_per_hour
from agents.agent_monitor import MonitorAgent
from agents.agent_control import ControlAgent
from agents.agent_read import ReadAgent
from agents.agent_voice import VoiceAgent
from agents.agent_supervisor import SupervisorAgent


class Pipeline:
    def __init__(self):
        self.simulator  = PlantSimulator()
        self.monitor    = MonitorAgent()
        self.control    = ControlAgent(self.simulator)
        self.reader     = ReadAgent()
        self.voice      = VoiceAgent()
        self.supervisor = SupervisorAgent(self.simulator, self.control, self.voice)
        self.decisions  = []
        self.total_saving = 0.0

    def tick(self) -> dict:
        """Run one tick. Returns state, any alerts, and any new decision."""
        state  = self.simulator.get_current_state()
        alerts = self.monitor.check(state)
        cost   = compute_cost_per_hour(state)

        new_decision = None
        if alerts:
            new_decision = self.supervisor.handle(alerts, state)
            if new_decision:
                self.decisions.append(new_decision)
                self.total_saving += new_decision.get("cost_impact", 0.0)

        self.simulator.advance()

        return {
            "hour":         self.simulator.current_hour,
            "state":        state,
            "alerts":       alerts,
            "cost":         cost,
            "new_decision": new_decision,
            "finished":     self.simulator.finished,
        }

    def reset(self):
        self.simulator.reset()
        self.monitor    = MonitorAgent()
        self.decisions  = []
        self.total_saving = 0.0
