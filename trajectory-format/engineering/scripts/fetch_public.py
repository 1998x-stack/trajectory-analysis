#!/usr/bin/env python3
"""Opt-in fetch of public upstream trajectory fixtures (not bundled/relicensed).

Network required. Inspect remote licenses, privacy and secrets before publishing.
"""
import argparse
import json
import urllib.request
from pathlib import Path

SOURCES = {
    "claude-code": {
        "url": "https://raw.githubusercontent.com/frederick-douglas-pearce/claude-code-sessions/main/fixtures/sanitized/retry-rate-mixed-tools.jsonl",
        "filename": "claude-code.jsonl",
        "quality": "sanitized Claude Code real session from upstream documentation",
    },
    "codex": {
        "url": "https://huggingface.co/datasets/cfahlgren1/codex-sessions/resolve/main/rollout-2026-03-27T09-21-37-019d2fac-0b38-70f0-baff-a394265d8291.jsonl",
        "filename": "codex.jsonl",
        "quality": "raw Codex CLI session; dataset license: other, inspect rights",
    },
    "openhands": {
        "url": "https://raw.githubusercontent.com/OpenHands/OpenHands/main/__tests__/fixtures/session-socket/reconnect-mid-stream.agent-server-1.47.0.json",
        "filename": "openhands.json",
        "quality": "captured OpenHands integration-session event stream using mock LLM (NOT real-model inference)",
    },
    "swe-agent": {
        "url": "https://raw.githubusercontent.com/SWE-agent/SWE-agent/main/trajectories/demonstrations/function_calling_simple.traj",
        "filename": "swe-agent.traj",
        "quality": "published SWE-agent demonstration trajectory; not a production trace",
    },
}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--accept-source-terms", action="store_true",
                   help="Confirm upstream licenses, usage policies and privacy have been reviewed")
    p.add_argument("--outdir", default="fixtures/real")
    p.add_argument("--only", choices=tuple(SOURCES))
    args = p.parse_args()
    if not args.accept_source_terms:
        p.error("Read SOURCES and pass --accept-source-terms to download")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for key, meta in SOURCES.items():
        if args.only and args.only != key:
            continue
        req = urllib.request.Request(meta["url"], headers={"User-Agent": "trajlab-research/0.1"})
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read(15 * 1024 * 1024 + 1)
        if len(body) > 15 * 1024 * 1024:
            raise ValueError("Remote trajectory over 15MiB cap: " + key)
        s = body.decode("utf-8")
        if meta["filename"].endswith(".jsonl"):
            for ln, line in enumerate(s.splitlines(), 1):
                if line.strip():
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"{key}:{ln} malformed JSONL") from exc
        else:
            json.loads(s)
        dest = outdir / meta["filename"]
        dest.write_text(s, encoding="utf-8")
        print(f"{key}: wrote {len(body)} bytes -> {dest} ({meta['quality']})")
    print("WARNING: real records may contain secrets; fixtures/real is gitignored.")

if __name__ == "__main__":
    main()
