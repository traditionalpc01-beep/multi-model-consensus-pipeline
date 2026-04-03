from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class StateStore:
    def __init__(self, project_dir: str | Path) -> None:
        self.project_dir = Path(project_dir)
        self.state_dir = self.project_dir / ".pipeline-state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "state.json"
        self.history_file = self.state_dir / "history.jsonl"

    def save_state(self, state_dict: Mapping[str, Any]) -> dict[str, Any]:
        state = dict(state_dict)
        self.state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return state

    def load_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {}
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def append_history(self, entry: Mapping[str, Any]) -> dict[str, Any]:
        history_entry = dict(entry)
        with self.history_file.open("a", encoding="utf-8") as history_file:
            history_file.write(json.dumps(history_entry, ensure_ascii=False))
            history_file.write("\n")
        return history_entry

    def get_history(self) -> list[dict[str, Any]]:
        if not self.history_file.exists():
            return []

        history: list[dict[str, Any]] = []
        with self.history_file.open("r", encoding="utf-8") as history_file:
            for line in history_file:
                line = line.strip()
                if line:
                    history.append(json.loads(line))
        return history
