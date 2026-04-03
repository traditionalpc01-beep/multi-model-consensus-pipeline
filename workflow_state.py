import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKFLOW_STATES = {
    "INIT": "初始化",
    "PROBING": "能力探测",
    "ROUTING": "任务路由",
    "CONSENSUS_ROUND_1": "共识第一轮",
    "CONSENSUS_ROUND_2": "共识第二轮",
    "CONSENSUS_ROUND_3": "共识第三轮",
    "CONSENSUS_TIMEOUT": "共识超时",
    "FINAL_PLAN": "最终方案生成",
    "EXECUTING": "执行编码",
    "REVIEWING": "联合复查",
    "REVIEW_FIX_1": "修复第1轮",
    "REVIEW_FIX_2": "修复第2轮",
    "REVIEW_TIMEOUT": "修复超时",
    "COMPLETED": "完成",
    "FUSED": "熔断终止",
    "HUMAN_ESCALATION": "人工介入",
}

STATE_TRANSITIONS = {
    "INIT": ["PROBING"],
    "PROBING": ["ROUTING", "FUSED"],
    "ROUTING": ["CONSENSUS_ROUND_1", "FINAL_PLAN", "FUSED"],
    "CONSENSUS_ROUND_1": ["CONSENSUS_ROUND_2", "FINAL_PLAN", "CONSENSUS_TIMEOUT"],
    "CONSENSUS_ROUND_2": ["CONSENSUS_ROUND_3", "FINAL_PLAN", "CONSENSUS_TIMEOUT"],
    "CONSENSUS_ROUND_3": ["CONSENSUS_TIMEOUT", "FINAL_PLAN"],
    "CONSENSUS_TIMEOUT": ["HUMAN_ESCALATION", "FINAL_PLAN"],
    "FINAL_PLAN": ["EXECUTING"],
    "EXECUTING": ["REVIEWING"],
    "REVIEWING": ["COMPLETED", "REVIEW_FIX_1", "REVIEW_TIMEOUT"],
    "REVIEW_FIX_1": ["REVIEWING", "REVIEW_FIX_2", "REVIEW_TIMEOUT"],
    "REVIEW_FIX_2": ["REVIEWING", "REVIEW_TIMEOUT"],
    "REVIEW_TIMEOUT": ["HUMAN_ESCALATION"],
    "FUSED": ["HUMAN_ESCALATION"],
    "HUMAN_ESCALATION": ["FINAL_PLAN", "COMPLETED", "FUSED"],
}


class InvalidWorkflowStateError(ValueError):
    """Raised when an unknown workflow state is used."""


class InvalidStateTransitionError(ValueError):
    """Raised when a state transition is not allowed."""

    def __init__(self, from_state: str, to_state: str, allowed_states: list[str]) -> None:
        super().__init__(
            f"Cannot transition from {from_state} to {to_state}. "
            f"Allowed transitions: {allowed_states}"
        )
        self.from_state = from_state
        self.to_state = to_state
        self.allowed_states = allowed_states


class WorkflowStateMachine:
    def __init__(self, project_dir: str | Path) -> None:
        self.project_dir = Path(project_dir)
        self.state_dir = self.project_dir / ".pipeline-state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.workflow_file = self.state_dir / "workflow.json"

        if self.workflow_file.exists():
            self._load()
        else:
            self._current_state = "INIT"
            self._history = [self._make_history_entry(None, "INIT")]
            self._persist()

    @property
    def current_state(self) -> str:
        return self._current_state

    def can_transition_to(self, target_state: str) -> bool:
        self._ensure_known_state(target_state)
        return target_state in STATE_TRANSITIONS.get(self._current_state, [])

    def transition_to(self, target_state: str) -> str:
        self._ensure_known_state(target_state)

        allowed_states = STATE_TRANSITIONS.get(self._current_state, [])
        if target_state not in allowed_states:
            raise InvalidStateTransitionError(self._current_state, target_state, allowed_states)

        self._history.append(self._make_history_entry(self._current_state, target_state))
        self._current_state = target_state
        self._persist()
        return self._current_state

    def get_state_history(self) -> list[dict[str, Any]]:
        return [entry.copy() for entry in self._history]

    def _load(self) -> None:
        payload = json.loads(self.workflow_file.read_text(encoding="utf-8"))
        current_state = payload["current_state"]
        self._ensure_known_state(current_state)

        history = payload.get("history", [])
        if not history:
            history = [self._make_history_entry(None, current_state)]

        self._current_state = current_state
        self._history = history

    def _persist(self) -> None:
        payload = {
            "current_state": self._current_state,
            "history": self._history,
        }
        self.workflow_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _ensure_known_state(self, state: str) -> None:
        if state not in WORKFLOW_STATES:
            raise InvalidWorkflowStateError(f"Unknown workflow state: {state}")

    @staticmethod
    def _make_history_entry(from_state: str | None, to_state: str) -> dict[str, Any]:
        return {
            "from_state": from_state,
            "to_state": to_state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
