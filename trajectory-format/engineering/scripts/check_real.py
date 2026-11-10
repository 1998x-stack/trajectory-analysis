#!/usr/bin/env python3
"""Compare the five externally sourced/runtime traces; logs aggregate statistics only."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from trajlab import convert, dump

SAMPLES = {
    "claude-code": "claude-code.jsonl",
    "codex": "codex.jsonl",
    "openhands": "openhands.json",
    "langgraph": "langgraph.json",
    "swe-agent": "swe-agent.traj",
}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", default="fixtures/real")
    p.add_argument("--report", default="/tmp/trajlab-real-summary.json")
    args = p.parse_args()
    root = Path(args.input_dir)
    rows = []
    for fmt, name in SAMPLES.items():
        src = root / name
        if not src.is_file():
            raise FileNotFoundError(src)
        obj, loss = convert(src, fmt)
        if not obj["events"]:
            raise AssertionError(fmt + ": produced no canonical events")
        kinds = sorted(set(e["kind"] for e in obj["events"]))
        rows.append({
            "format": fmt,
            "input_records": loss["input_record_count"],
            "output_events": loss["output_event_count"],
            "mapped_leaves": loss["mapped_leaf_count"],
            "omitted_leaves": loss["omitted_leaf_count"],
            "mapped_leaf_ratio": loss["mapped_leaf_ratio"],
            "event_kinds": kinds,
            "warning_count": len(loss["warnings"])
        })
        print(fmt + ": " + str(loss["input_record_count"]) + " source records → " +
              str(loss["output_event_count"]) + " events; " +
              str(loss["mapped_leaf_count"]) + " mapped / " +
              str(loss["omitted_leaf_count"]) + " omitted leaves; " +
              "warnings=" + str(len(loss["warnings"])))
    dump(args.report, {
        "metric_note": "JSON leaf-path classification by adapters, not semantic fidelity or reversibility",
        "samples": rows
    })
    print("Aggregate-only report: " + args.report)

if __name__ == "__main__":
    main()
