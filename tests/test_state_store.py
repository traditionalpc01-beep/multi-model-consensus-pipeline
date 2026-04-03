import json
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from state_store import StateStore


class StateStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path.cwd() / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        self.project_dir = temp_root / f"state-store-{uuid4().hex}"
        self.project_dir.mkdir()
        self.store = StateStore(self.project_dir)

    def tearDown(self) -> None:
        if self.project_dir.exists():
            shutil.rmtree(self.project_dir)

    def test_initialization_uses_pipeline_state_paths(self) -> None:
        self.assertEqual(self.store.state_file, self.project_dir / ".pipeline-state" / "state.json")
        self.assertEqual(
            self.store.history_file,
            self.project_dir / ".pipeline-state" / "history.jsonl",
        )
        self.assertTrue(self.store.state_dir.exists())

    def test_save_state_and_load_state_round_trip(self) -> None:
        state = {
            "task_id": "task-123",
            "status": "working",
            "iteration": 1,
        }

        saved_state = self.store.save_state(state)

        self.assertEqual(saved_state, state)
        self.assertEqual(self.store.load_state(), state)
        self.assertEqual(
            json.loads(self.store.state_file.read_text(encoding="utf-8")),
            state,
        )

    def test_load_state_returns_empty_dict_when_missing(self) -> None:
        self.assertEqual(self.store.load_state(), {})

    def test_append_history_and_get_history_preserve_order(self) -> None:
        first_entry = {"event": "prepare_context", "status": "started"}
        second_entry = {"event": "prepare_context", "status": "completed"}

        self.store.append_history(first_entry)
        self.store.append_history(second_entry)

        history = self.store.get_history()

        self.assertEqual(history, [first_entry, second_entry])
        self.assertEqual(
            self.store.history_file.read_text(encoding="utf-8").strip().splitlines(),
            [
                json.dumps(first_entry, ensure_ascii=False),
                json.dumps(second_entry, ensure_ascii=False),
            ],
        )


if __name__ == "__main__":
    unittest.main()
