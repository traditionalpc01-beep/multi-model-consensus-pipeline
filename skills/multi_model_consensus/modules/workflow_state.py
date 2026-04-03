
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


WORKFLOW_STATES = [
    "INIT", "PROBING", "ROUTING", "CONSENSUS_ROUND_1",
    "CONSENSUS_ROUND_2", "CONSENSUS_ROUND_3", "CONSENSUS_TIMEOUT",
    "FINAL_PLAN", "EXECUTING", "REVIEWING", "REVIEW_FIX_1",
    "REVIEW_FIX_2", "REVIEW_TIMEOUT", "COMPLETED", "FUSED",
    "HUMAN_ESCALATION"
]


class WorkflowState:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.state_dir = project_dir / ".skill-state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "state.json"
        self.history_file = self.state_dir / "history.jsonl"
        
        self._state = {}
        self._history = []
        self._load()
    
    def _load(self):
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self._state = json.load(f)
        else:
            self._state = {
                "current_state": "INIT",
                "context": {},
                "capability_level": None,
                "consensus_results": [],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self._save()
        
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._history.append(json.loads(line))
    
    def _save(self):
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)
    
    def _append_history(self, entry):
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._history.append(entry)
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    def get_state(self):
        return self._state.copy()
    
    def set_context(self, context):
        self._state["context"] = context
        self._append_history({"event": "set_context", "context": context})
        self._save()
    
    def set_capability_level(self, level):
        self._state["capability_level"] = level.value if hasattr(level, 'value') else level
        self._append_history({"event": "set_capability_level", "level": self._state["capability_level"]})
        self._save()
    
    def add_consensus_result(self, result):
        self._state["consensus_results"].append(result)
        self._append_history({"event": "add_consensus_result", "result": result})
        self._save()
    
    def reset(self):
        self._state = {
            "current_state": "INIT",
            "context": {},
            "capability_level": None,
            "consensus_results": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._history = []
        if self.history_file.exists():
            self.history_file.unlink()
        self._save()

