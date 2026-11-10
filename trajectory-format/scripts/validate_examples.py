#!/usr/bin/env python3
"""Offline structural checks for trajectory-format examples (standard library only).

This is not official ATIF/OTLP/STS full-schema certification.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

def require(condition, explanation):
    if not condition:
        raise AssertionError(explanation)

def unique_nonempty(items, label):
    require(all(isinstance(x, str) and x for x in items), label + " contains empty/nonstring ID")
    require(len(items) == len(set(items)), label + " has duplicate IDs")

def load_examples():
    found = {}
    for path in sorted(EXAMPLES.iterdir()):
        if path.suffix == ".json":
            found[path.name] = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix == ".jsonl":
            rows = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]
            require(rows, path.name + " must be nonempty")
            found[path.name] = rows
    return found

def check_atif(a):
    require(a["schema_version"] == "ATIF-v1.8", "ATIF version")
    require(a["agent"]["name"] and a["agent"]["version"], "ATIF agent")
    steps = a["steps"]
    require([s["step_id"] for s in steps] == list(range(1, len(steps)+1)), "ATIF step ids")
    ids = []
    observed = []
    for s in steps:
        require(s["source"] in ("system", "user", "agent"), "ATIF source")
        for call in s.get("tool_calls", []):
            require(isinstance(call["arguments"], dict), "ATIF tool args must be object")
            ids.append(call["tool_call_id"])
        for result in s.get("observation", {}).get("results", []):
            if "source_call_id" in result:
                observed.append(result["source_call_id"])
    unique_nonempty(ids, "ATIF calls")
    require(set(observed).issubset(set(ids)), "ATIF unmatched observation")

def check_sts(lines):
    h = lines[0]
    require(h.get("type") == "session" and h.get("harness") and h.get("id"), "STS header")
    ids, results = [], []
    for line in lines[1:]:
        require(line.get("type") == "message", "STS message envelope")
        m = line["message"]
        require(m.get("role") in ("user", "assistant", "system", "tool"), "STS role")
        require("content" in m and isinstance(m["content"], str), "STS text content")
        for call in m.get("toolCalls", []):
            json.loads(call["function"]["arguments"])
            ids.append(call["id"])
        if "toolCallId" in m:
            results.append(m["toolCallId"])
    unique_nonempty(ids, "STS calls")
    require(set(results).issubset(set(ids)), "STS unmatched tool result")

def check_event_stream(lines):
    unique_nonempty([x["event_id"] for x in lines], "event IDs")
    require([x["sequence"] for x in lines] == list(range(1, len(lines)+1)), "event sequence")
    calls = {x.get("tool_call_id") for x in lines if x["event_type"] == "tool_call"}
    for x in lines:
        if x["event_type"] == "tool_result":
            require(x.get("tool_call_id") in calls, "event unmatched tool result")

def check_canonical(c):
    require(c["schema_version"] == "0.1.0" and c["session_id"], "canonical metadata")
    ev = c["events"]
    unique_nonempty([x["event_id"] for x in ev], "canonical event ids")
    require([x["sequence"] for x in ev] == list(range(1, len(ev)+1)), "canonical sequence")
    names = {x["event_id"] for x in ev}
    for x in ev:
        require(x["event_type"] in {"message", "tool_call", "tool_result", "state_update", "checkpoint", "handoff", "error"}, "canonical event type")
        require(x["source"]["format"] and x["source"]["raw_ref"], "canonical source")
        if x.get("parent_event_id"):
            require(x["parent_event_id"] in names, "canonical parent missing")

def check_otlp(o):
    spans = [s for r in o["resourceSpans"] for scope in r["scopeSpans"] for s in scope["spans"]]
    ids = [x["spanId"] for x in spans]
    unique_nonempty(ids, "span ids")
    for s in spans:
        require(re.fullmatch(r"[0-9a-f]{32}", s["traceId"]) is not None, "traceId hex")
        require(re.fullmatch(r"[0-9a-f]{16}", s["spanId"]) is not None, "spanId hex")
        if s.get("parentSpanId"):
            require(s["parentSpanId"] in ids, "missing parent span")
        require(int(s["endTimeUnixNano"]) >= int(s["startTimeUnixNano"]), "negative span time")

def main():
    e = load_examples()
    expected = {
        "openai-chat-messages.json", "openai-responses-items.json",
        "anthropic-content-blocks.json", "atif-v1.8.json",
        "hf-sts.jsonl", "custom-event-stream.jsonl", "otlp-genai.json",
        "openinference-logical-spans.json", "rl-episode.json",
        "canonical-trajectory.json"
    }
    require(set(e) == expected, "example file set changed: " + repr(set(e) ^ expected))
    check_atif(e["atif-v1.8.json"])
    check_sts(e["hf-sts.jsonl"])
    check_event_stream(e["custom-event-stream.jsonl"])
    check_canonical(e["canonical-trajectory.json"])
    check_otlp(e["otlp-genai.json"])
    calls = e["openai-chat-messages.json"]["messages"][1]["tool_calls"]
    for call in calls:
        json.loads(call["function"]["arguments"])
    for item in e["openai-responses-items.json"]["input"]:
        if item.get("type") == "function_call":
            json.loads(item["arguments"])
    for msg in e["anthropic-content-blocks.json"]["messages"]:
        if isinstance(msg["content"], list):
            for block in msg["content"]:
                if block["type"] == "tool_use":
                    require(isinstance(block["input"], dict), "Anthropic tool_use input")
    print("PASS: parsed " + str(len(e)) + " example files (JSON/JSONL); structural checks passed")
    print("NOTE: this does not certify official ATIF, STS, OpenAI or OTLP conformance.")

if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, json.JSONDecodeError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        raise SystemExit(1)
