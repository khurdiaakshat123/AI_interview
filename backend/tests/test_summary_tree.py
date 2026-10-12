import unittest
from backend.app.engines.interview_state import InterviewState, ItemState, SummaryNode


class TestSummaryTree(unittest.TestCase):
    """
    Rigorously tests the Stack-based Recursive Summary Tree & Immutable Checkpointing.
    Validates:
    - Root Node A initialization
    - Recursive branch progression: S(child) = S(child, S(parent))
    - Backtracking restores immutable snapshots
    - Topic archiving from pruned branches to prevent repeated questions
    - State serialization fidelity
    """

    def setUp(self):
        self.state = InterviewState(session_id="sess_summary_test")
        self.state.register_item(
            item_id="proj_distributed_cache",
            item_type="PROJECT",
            phase="PROJECT_DEFENSE",
            title="Distributed Caching System",
            details="Engineered Raft-based distributed cache with custom LSM storage and write-ahead logs."
        )

    def test_root_node_initialization(self):
        # Starting an item must automatically create and activate Root Node A
        self.assertTrue(self.state.start_item("proj_distributed_cache"))
        self.assertEqual(self.state.active_summary_node_id, "node_proj_distributed_cache_root")
        
        root = self.state.summary_nodes.get(self.state.active_summary_node_id)
        self.assertIsNotNone(root)
        self.assertIn("Distributed Caching System", root.accumulated_summary)
        self.assertIn("Raft-based", root.accumulated_summary)
        self.assertEqual(root.turn_index, 0)

    def test_recursive_branch_progression(self):
        self.state.start_item("proj_distributed_cache")
        root_summary = self.state.get_active_branch_summary("proj_distributed_cache")

        # Turn 1: Node B (Follow-up 1)
        node_b = self.state.record_summary_turn(
            turn_index=1,
            item_id="proj_distributed_cache",
            question_text="How did you implement consensus?",
            answer_understanding="Candidate used Raft leader election with 150ms heartbeats.",
            reasoning_summary="Avoided split-brain via strict quorum.",
            candidate_topics=["Raft", "Consensus"],
            entities=["Raft"]
        )

        self.assertEqual(node_b.node_id, "node_proj_distributed_cache_t1")
        self.assertEqual(node_b.parent_id, "node_proj_distributed_cache_root")
        self.assertEqual(self.state.active_summary_node_id, "node_proj_distributed_cache_t1")
        self.assertIn("Follow-up 1: Candidate used Raft", node_b.accumulated_summary)
        self.assertIn("Avoided split-brain", node_b.accumulated_summary)

        # Turn 2: Node C (Sub-follow-up to B) -> S(C) = S(C, S(B, S(A)))
        node_c = self.state.record_summary_turn(
            turn_index=2,
            item_id="proj_distributed_cache",
            question_text="What happens when the leader partitions?",
            answer_understanding="Candidate explained term increments and log rollback.",
            reasoning_summary="Reconnected leader steps down immediately.",
            candidate_topics=["Partition Handling"],
            entities=["Log Rollback"]
        )

        self.assertEqual(node_c.node_id, "node_proj_distributed_cache_t2")
        self.assertEqual(node_c.parent_id, "node_proj_distributed_cache_t1")
        self.assertEqual(self.state.active_summary_node_id, "node_proj_distributed_cache_t2")
        self.assertIn("Follow-up 1", node_c.accumulated_summary)
        self.assertIn("Follow-up 2", node_c.accumulated_summary)
        self.assertIn("Raft", node_c.topics_covered_in_branch)
        self.assertIn("Partition Handling", node_c.topics_covered_in_branch)

    def test_backtracking_restores_immutable_snapshot_and_archives_topics(self):
        self.state.start_item("proj_distributed_cache")

        # Go down Branch B -> C
        self.state.record_summary_turn(
            turn_index=1,
            item_id="proj_distributed_cache",
            question_text="Tell me about your consensus layer.",
            answer_understanding="Explained Raft implementation.",
            candidate_topics=["Raft", "Consensus"]
        )
        self.state.record_summary_turn(
            turn_index=2,
            item_id="proj_distributed_cache",
            question_text="Deep dive into partitioning.",
            answer_understanding="Candidate answered poorly on partition tolerance.",
            candidate_topics=["Split-Brain", "Partition Tolerance"]
        )

        # Candidate failed or finished Branch B -> Backtrack to Root Node A
        root_id = "node_proj_distributed_cache_root"
        restored_node = self.state.backtrack_to_node(root_id)

        # Verify active context is restored to clean Node A snapshot
        self.assertEqual(restored_node.node_id, root_id)
        self.assertEqual(self.state.active_summary_node_id, root_id)
        self.assertNotIn("Follow-up 1", restored_node.accumulated_summary)
        self.assertNotIn("Follow-up 2", restored_node.accumulated_summary)

        # Verify pruned topics are archived to prevent asking them in Branch E
        pruned = self.state.get_pruned_topics_for_item("proj_distributed_cache")
        self.assertIn("Raft", pruned)
        self.assertIn("Consensus", pruned)
        self.assertIn("Split-Brain", pruned)

    def test_serialization_roundtrip(self):
        self.state.start_item("proj_distributed_cache")
        self.state.record_summary_turn(
            turn_index=1,
            item_id="proj_distributed_cache",
            question_text="Q1",
            answer_understanding="A1 understanding",
            candidate_topics=["Topic1"]
        )

        # Serialize to dict and reload
        state_dict = self.state.to_dict()
        rehydrated = InterviewState.from_dict(state_dict)

        self.assertEqual(rehydrated.active_summary_node_id, "node_proj_distributed_cache_t1")
        self.assertEqual(len(rehydrated.summary_nodes), 2)  # root + turn 1
        self.assertIn("Topic1", rehydrated.summary_nodes["node_proj_distributed_cache_t1"].topics_covered_in_branch)


if __name__ == "__main__":
    unittest.main()
