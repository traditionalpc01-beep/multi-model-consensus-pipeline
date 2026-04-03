
from __future__ import annotations

import os
from pathlib import Path

from .modules import task_router
from .modules import capability_probe
from .modules import consensus_engine
from .modules import workflow_state


class MultiModelConsensusSkill:
    def __init__(self, project_dir=None):
        self.project_dir = Path(project_dir or os.getcwd())
        self.state = workflow_state.WorkflowState(self.project_dir)
        self.task_router = task_router.TaskRouter()
        self.capability_probe = capability_probe.CapabilityProbe()
        self.consensus_engine = consensus_engine.ConsensusEngine()
    
    def prepare_context(self, task, context_files=None):
        route_choice = self.task_router.route(task)
        context = {
            "task": task,
            "route_choice": route_choice.to_dict(),
            "context_files": context_files or []
        }
        self.state.set_context(context)
        return {
            "success": True,
            "route_choice": route_choice.to_dict(),
            "context": context
        }
    
    def probe_capability(self, capability_score=0.8):
        level, action = self.capability_probe.get_capability_action(capability_score)
        self.state.set_capability_level(level)
        return {
            "success": True,
            "level": level.value if hasattr(level, 'value') else level,
            "action": action
        }
    
    def run_consensus_round(self, qwen_analysis, codex_analysis):
        consensus_result = self.consensus_engine.check(qwen_analysis, codex_analysis)
        self.state.add_consensus_result(consensus_result)
        return {
            "success": True,
            "consensus_result": consensus_result
        }
    
    def get_workflow_state(self):
        return {
            "success": True,
            "state": self.state.get_state()
        }
    
    def reset(self):
        self.state.reset()
        return {"success": True}

