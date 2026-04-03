import json
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from workflow_state import (
    STATE_TRANSITIONS,
    WORKFLOW_STATES,
    InvalidStateTransitionError,
    WorkflowStateMachine,
)


class WorkflowStateMachineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path.cwd() / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        self.project_dir = temp_root / f"workflow-state-{uuid4().hex}"
        self.project_dir.mkdir()

    def tearDown(self) -> None:
        if self.project_dir.exists():
            shutil.rmtree(self.project_dir)

    def test_initialization_creates_workflow_file_with_init_state(self) -> None:
        machine = WorkflowStateMachine(self.project_dir)

        workflow_file = self.project_dir / ".pipeline-state" / "workflow.json"

        self.assertEqual(machine.current_state, "INIT")
        self.assertTrue(workflow_file.exists())
        self.assertEqual(
            machine.get_state_history(),
            [
                {
                    "from_state": None,
                    "to_state": "INIT",
                    "timestamp": machine.get_state_history()[0]["timestamp"],
                }
            ],
        )

        persisted = json.loads(workflow_file.read_text(encoding="utf-8"))
        self.assertEqual(persisted["current_state"], "INIT")
        self.assertEqual(len(persisted["history"]), 1)

    def test_can_transition_to_uses_transition_rules(self) -> None:
        machine = WorkflowStateMachine(self.project_dir)

        self.assertTrue(machine.can_transition_to("PROBING"))
        self.assertFalse(machine.can_transition_to("FINAL_PLAN"))
        self.assertEqual(STATE_TRANSITIONS["INIT"], ["PROBING"])

    def test_transition_to_updates_state_and_history(self) -> None:
        machine = WorkflowStateMachine(self.project_dir)

        machine.transition_to("PROBING")
        machine.transition_to("ROUTING")

        self.assertEqual(machine.current_state, "ROUTING")
        self.assertEqual(
            [entry["to_state"] for entry in machine.get_state_history()],
            ["INIT", "PROBING", "ROUTING"],
        )

    def test_transition_to_rejects_invalid_transition(self) -> None:
        machine = WorkflowStateMachine(self.project_dir)

        with self.assertRaises(InvalidStateTransitionError) as ctx:
            machine.transition_to("FINAL_PLAN")

        self.assertIn("INIT", str(ctx.exception))
        self.assertIn("FINAL_PLAN", str(ctx.exception))
        self.assertEqual(machine.current_state, "INIT")
        self.assertEqual(len(machine.get_state_history()), 1)

    def test_existing_workflow_file_is_loaded(self) -> None:
        machine = WorkflowStateMachine(self.project_dir)
        machine.transition_to("PROBING")

        reloaded = WorkflowStateMachine(self.project_dir)

        self.assertEqual(reloaded.current_state, "PROBING")
        self.assertEqual(
            [entry["to_state"] for entry in reloaded.get_state_history()],
            ["INIT", "PROBING"],
        )


class WorkflowStateConstantsTestCase(unittest.TestCase):
    def test_workflow_states_cover_architecture_states(self) -> None:
        expected_states = {
            "INIT",
            "PROBING",
            "ROUTING",
            "CONSENSUS_ROUND_1",
            "CONSENSUS_ROUND_2",
            "CONSENSUS_ROUND_3",
            "CONSENSUS_TIMEOUT",
            "FINAL_PLAN",
            "EXECUTING",
            "REVIEWING",
            "REVIEW_FIX_1",
            "REVIEW_FIX_2",
            "REVIEW_TIMEOUT",
            "COMPLETED",
            "FUSED",
            "HUMAN_ESCALATION",
        }

        self.assertEqual(set(WORKFLOW_STATES), expected_states)


if __name__ == "__main__":
    unittest.main()
