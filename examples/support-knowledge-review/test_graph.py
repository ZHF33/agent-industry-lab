"""Scripted control tests, not real model validation. Run manually if desired."""
import json
from pathlib import Path
import unittest
from langgraph.types import Command
from graph_agent import build_graph


def call(name):
    return {"function": {"name": name, "arguments": {"request_id": "REQUEST-DEMO-01"}}}


def evidence():
    return {"role": "assistant", "content": "", "tool_calls": [
        call("lookup_request"), call("search_knowledge"), call("assess_retrieval")]}


def answer():
    return {"role": "assistant", "content": "retrieval-assessment-demo-01: KB-DEMO-RETURN-v2 is a scoped candidate. Order eligibility still needs human checks; no customer message sent."}


class GraphTests(unittest.TestCase):
    def ticket(self):
        return json.loads(Path(__file__).with_name("sample.json").read_text())

    def test_review(self):
        replies = iter([evidence(), answer()])
        graph = build_graph(lambda messages: next(replies))
        config = {"configurable": {"thread_id": "demo-review"}, "recursion_limit": 16}
        graph.invoke({"ticket": self.ticket()}, config)
        self.assertEqual(graph.get_state(config).next, ("review",))
        result = graph.invoke(Command(resume={"decision": "approve", "reviewer": "test"}), config)
        self.assertEqual(result["result"]["status"], "reviewed")
        self.assertFalse(result["result"]["actions_executed"])
        self.assertEqual(len(result["result"]["tool_trace"]), 3)

    def test_tool_error_can_be_corrected(self):
        replies = iter([{"role": "assistant", "tool_calls": [call("not_allowed")]}, evidence(), answer()])
        graph = build_graph(lambda messages: next(replies))
        config = {"configurable": {"thread_id": "demo-correct"}, "recursion_limit": 16}
        graph.invoke({"ticket": self.ticket()}, config)
        self.assertEqual(graph.get_state(config).next, ("review",))
        trace = graph.get_state(config).values["result"]["tool_trace"]
        self.assertIn("error", trace[0])

    def test_missing_passage_citation_requires_correction(self):
        replies = iter([evidence(), {"role": "assistant", "content": "retrieval-assessment-demo-01 only"}, answer()])
        graph = build_graph(lambda messages: next(replies))
        config = {"configurable": {"thread_id": "demo-citation"}, "recursion_limit": 16}
        graph.invoke({"ticket": self.ticket()}, config)
        self.assertEqual(graph.get_state(config).values["result"]["model_rounds"], 3)

    def test_stale_request_has_no_candidates(self):
        ticket = self.ticket(); ticket["as_of"] = "2026-10-26T12:02:00+00:00"
        replies = iter([evidence(), {"role": "assistant", "content": "retrieval-assessment-demo-01: insufficient evidence; human review required."}])
        graph = build_graph(lambda messages: next(replies))
        config = {"configurable": {"thread_id": "demo-empty"}, "recursion_limit": 16}
        graph.invoke({"ticket": ticket}, config)
        report = graph.get_state(config).values["result"]["retrieval_report"][0][0]
        self.assertEqual(report["candidate_source_ids"], [])
        self.assertEqual(report["status"], "insufficient_evidence")

    def test_round_limit(self):
        graph = build_graph(lambda messages: evidence())
        with self.assertRaisesRegex(RuntimeError, "round limit"):
            graph.invoke({"ticket": self.ticket()}, {"configurable": {"thread_id": "demo-limit"}, "recursion_limit": 16})


if __name__ == "__main__":
    unittest.main()
