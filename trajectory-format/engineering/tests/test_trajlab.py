"""Unit tests for five native adapters and audited field mappings."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from trajlab import convert, detect, leaves, dump, read_records

FX = ROOT / "fixtures" / "smoke"


class AdapterTests(unittest.TestCase):
    def test_all_five_formats(self):
        files = {"claude-code": "claude-code.jsonl", "codex": "codex.jsonl",
                 "openhands": "openhands.json", "langgraph": "langgraph.json",
                 "swe-agent": "swe-agent.traj"}
        for name, file in files.items():
            with self.subTest(fmt=name):
                path = FX / file
                self.assertEqual(detect(read_records(path)), name)
                obj, loss = convert(path)
                self.assertEqual(obj["source_format"], name)
                self.assertGreater(len(obj["events"]), 0)
                self.assertEqual([v["sequence"] for v in obj["events"]],
                                 list(range(1, len(obj["events"]) + 1)))
                self.assertGreater(loss["mapped_leaf_count"], 0)
                self.assertEqual(loss["output_event_count"], len(obj["events"]))
                self.assertTrue(all(e["kind"] and e["actor"] and e["source"]["sha256"] for e in obj["events"]))

    def test_tool_pairing_and_no_double_count_codex(self):
        for file in ("claude-code.jsonl", "codex.jsonl", "openhands.json", "swe-agent.traj"):
            obj, loss = convert(FX / file)
            calls = [x["call_id"] for x in obj["events"] if x["kind"] == "tool_call"]
            results = [x["call_id"] for x in obj["events"] if x["kind"] == "tool_result"]
            self.assertTrue(set(results).issubset(set(calls)), file)
            self.assertFalse(any("unmatched" in w for w in loss["warnings"]), file)
        obj, _ = convert(FX / "codex.jsonl")
        self.assertEqual(1, len([x for x in obj["events"] if x["kind"] == "message" and x["actor"] == "user"]))

    def test_field_level_loss_is_explicit(self):
        _, r = convert(FX / "codex.jsonl")
        self.assertGreater(r["omitted_leaf_count"], 0)
        self.assertIn("/payload/base_instructions/text", r["records"][0]["omitted"])
        self.assertIn("/payload/id", r["records"][0]["mapped"])
        self.assertIn("not semantic fidelity", r["metric_definition"].lower())

    def test_claude_content_block_and_source_chain(self):
        obj, _ = convert(FX / "claude-code.jsonl")
        self.assertEqual("Bash", [e for e in obj["events"] if e["kind"] == "tool_call"][0]["payload"]["name"])
        self.assertEqual("/workspace", [e for e in obj["events"] if e["kind"] == "tool_result"][0]["payload"]["content"])
        self.assertTrue(any(e.get("parent_source_id") == "cl-u1" for e in obj["events"]))

    def test_openhands_socket_capture_dedup(self):
        src = json.loads((FX / "openhands.json").read_text())
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "openhands.json"
            p.write_text(json.dumps({"before": src[:2], "after": src}))
            obj, _ = convert(p, "openhands")
            self.assertEqual(4, len(obj["events"]))

    def test_langgraph_history_reverse_order_is_preserved(self):
        obj, _ = convert(FX / "langgraph.json")
        self.assertEqual(["checkpoint", "checkpoint"], [e["kind"] for e in obj["events"]])
        self.assertEqual(["checkpoint-2", "checkpoint-1"], [
            e["payload"]["config"]["configurable"]["checkpoint_id"] for e in obj["events"]])

    def test_malformed_jsonl_has_line_number(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "broken.jsonl"
            p.write_text('{"ok":true}\n{no}\n')
            with self.assertRaisesRegex(ValueError, r":2:"):
                read_records(p)

    def test_basic_json_schema_content(self):
        self.assertIn("/a/0/b", list(leaves({"a": [{"b": 1}]})))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.json"
            dump(path, {"hello": "world"})
            self.assertEqual("world", json.loads(path.read_text())["hello"])


if __name__ == "__main__":
    unittest.main()
