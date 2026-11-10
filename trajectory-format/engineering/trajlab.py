#!/usr/bin/env python3
"""Five native Agent trajectory adapters, canonical events, and auditable field loss.

Standard library only. Not an official schema implementation or lossless replay system.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

FORMATS = ("claude-code", "codex", "openhands", "langgraph", "swe-agent")
KINDS = {"message", "thought", "tool_call", "tool_result", "state", "checkpoint", "metadata", "error", "handoff"}
ACTORS = {"user", "assistant", "system", "tool", "environment", "agent"}
SKIP = object()


def leaves(value, base=""):
    """Leaf-level JSON Pointer paths. Empty collections count as one leaf."""
    if isinstance(value, dict) and value:
        for key, val in value.items():
            yield from leaves(val, base + "/" + str(key).replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list) and value:
        for i, val in enumerate(value):
            yield from leaves(val, base + "/" + str(i))
    else:
        yield base or "/"


def json_text(v):
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def preview(v):
    s = json_text(v).replace("\n", " ")
    return s[:180] + ("…" if len(s) > 180 else "")


def timestamp(v):
    if not v:
        return None
    try:
        datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return str(v)
    except (TypeError, ValueError):
        return None


def read_records(path):
    path = Path(path)
    if path.suffix == ".jsonl":
        records = []
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{n}: invalid JSON: {exc}") from exc
        return records
    return json.loads(path.read_text(encoding="utf-8"))


def detect(raw):
    if isinstance(raw, dict):
        if "trajectory" in raw and isinstance(raw["trajectory"], list):
            return "swe-agent"
        if "before" in raw or "after" in raw or "events" in raw:
            return "openhands"
        if "history" in raw and isinstance(raw["history"], list):
            first = raw["history"][0] if raw["history"] else {}
            if isinstance(first, dict) and first.get("role") in ("system", "user", "assistant", "tool"):
                return "swe-agent"
            return "langgraph"
        if "values" in raw and "next" in raw:
            return "langgraph"
    if isinstance(raw, list) and raw:
        obj = raw[0]
        if not isinstance(obj, dict):
            raise ValueError("Cannot detect list with non-object items")
        if "sessionId" in obj or "parentUuid" in obj:
            return "claude-code"
        if obj.get("type") in {"session_meta", "response_item", "event_msg", "turn_context"}:
            return "codex"
        if "values" in obj and "next" in obj or obj.get("type") in {"checkpoint", "task", "task_result"}:
            return "langgraph"
        if obj.get("kind") in {"MessageEvent", "ActionEvent", "ObservationEvent"} or "event" in obj:
            return "openhands"
    raise ValueError("Unrecognized format. Pass --format explicitly.")


class Builder:
    def __init__(self, fmt, source, session):
        self.fmt = fmt
        self.source = str(source)
        self.session = str(session)
        self.events = []
        self.seen = []
        self.warnings = []
        self._calls = set()
        self._results = []

    def mark(self, i, obj, paths=(), pointer=""):
        while len(self.seen) <= i:
            self.seen.append(None)
        if self.seen[i] is None:
            self.seen[i] = {"obj": obj, "mapped": set(), "pointer": pointer}
        for p in paths:
            self.seen[i]["mapped"].add(p)

    def emit(self, i, obj, kind, actor, summary, payload=None, used=(),
             when=None, call_id=None, parent=None, source_id=None, pointer=""):
        if kind not in KINDS or actor not in ACTORS:
            raise ValueError(f"Bad event kind/actor: {kind}/{actor}")
        self.mark(i, obj, used, pointer)
        seq = len(self.events) + 1
        digest = hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        event = {
            "event_id": f"ev-{seq:05d}", "sequence": seq,
            "kind": kind, "actor": actor,
            "summary": preview(summary),
            "payload": payload if isinstance(payload, dict) else {"value": payload},
            "source": {"record_index": i, "pointer": pointer, "sha256": digest, "source_id": source_id}
        }
        t = timestamp(when)
        if t:
            event["timestamp"] = t
        if call_id is not None:
            event["call_id"] = str(call_id)
            if kind == "tool_call":
                self._calls.add(str(call_id))
            elif kind == "tool_result":
                self._results.append(str(call_id))
        if parent is not None:
            event["parent_source_id"] = str(parent)
        self.events.append(event)

    def audit(self):
        details = []
        counts = Counter()
        for i, row in enumerate(self.seen):
            if row is None:
                continue
            all_paths = list(leaves(row["obj"]))
            mapped = []
            omitted = []
            for path in all_paths:
                if any(path == p or path.startswith(p + "/") for p in row["mapped"]):
                    mapped.append(path)
                else:
                    omitted.append(path)
            counts["mapped_leaves"] += len(mapped)
            counts["omitted_leaves"] += len(omitted)
            details.append({
                "record_index": i, "source_pointer": row["pointer"],
                "mapped": mapped, "omitted": omitted
            })
        for call in self._results:
            if call not in self._calls:
                self.warnings.append("unmatched tool result: " + call)
        total = counts["mapped_leaves"] + counts["omitted_leaves"]
        report = {
            "source_format": self.fmt, "session_id": self.session,
            "metric_definition": "Mapped/omitted JSON leaf paths classified by adapter. This is not semantic fidelity, reversibility, or byte-loss percentage.",
            "mapped_leaf_count": counts["mapped_leaves"],
            "omitted_leaf_count": counts["omitted_leaves"],
            "mapped_leaf_ratio": round(counts["mapped_leaves"] / total, 4) if total else None,
            "input_record_count": len([x for x in self.seen if x is not None]),
            "output_event_count": len(self.events),
            "warnings": self.warnings,
            "records": details
        }
        return report

    def result(self):
        return {
            "schema_version": "trajlab/v1",
            "source_format": self.fmt, "session_id": self.session,
            "source_file": self.source, "events": self.events
        }


def content_blocks(c):
    if isinstance(c, list):
        return c
    return [{"type": "text", "text": json_text(c)}]


def claude(raw, source):
    if not isinstance(raw, list):
        raise ValueError("Claude Code expects JSONL array of records")
    b = Builder("claude-code", source, next((r.get("sessionId") for r in raw if r.get("sessionId")), Path(source).stem))
    for i, r in enumerate(raw):
        typ = r.get("type")
        uid = r.get("uuid")
        t = r.get("timestamp")
        base = ["type", "uuid", "parentUuid", "timestamp", "sessionId"]
        common = ["/" + k for k in base if k in r]
        msg = r.get("message") or {}
        if typ in ("assistant", "user") and isinstance(msg, dict):
            blocks = content_blocks(msg.get("content", ""))
            if not blocks:
                b.mark(i, r, common, f"/{i}")
            for j, block in enumerate(blocks):
                c = block if isinstance(block, dict) else {"type": "text", "text": str(block)}
                kind = c.get("type", "text")
                used = common + [f"/message/content/{j}"] if isinstance(msg.get("content"), list) else common + ["/message/content"]
                if typ == "assistant":
                    used += ["/message/model", "/message/usage"]
                if kind == "tool_use":
                    b.emit(i, r, "tool_call", "assistant", c.get("name", "tool"),
                           {"name": c.get("name"), "arguments": c.get("input", {}), "block": c,
                            "model": msg.get("model"), "usage": msg.get("usage")},
                           used, t, c.get("id"), r.get("parentUuid"), uid, f"/{i}")
                elif kind == "tool_result":
                    b.emit(i, r, "tool_result", "tool", c.get("content", ""),
                           {"content": c.get("content"), "is_error": c.get("is_error", False),
                            "block": c}, used, t, c.get("tool_use_id"), r.get("parentUuid"), uid, f"/{i}")
                else:
                    who = "assistant" if typ == "assistant" else "user"
                    ekind = "thought" if kind in ("thinking", "redacted_thinking") else "message"
                    text = c.get("text", c.get("thinking", c))
                    b.emit(i, r, ekind, who, text, {"block": c, "model": msg.get("model"),
                           "usage": msg.get("usage")}, used, t, parent=r.get("parentUuid"), source_id=uid, pointer=f"/{i}")
        elif typ in ("system", "progress", "queue-operation"):
            # Keep top-level event metadata but not opaque nested progress payload.
            mapped = common + ["/subtype", "/durationMs", "/level"]
            b.emit(i, r, "error" if r.get("subtype") == "api_error" else "state",
                   "system", typ + ":" + str(r.get("subtype", "")),
                   {"type": typ, "subtype": r.get("subtype"), "duration_ms": r.get("durationMs"),
                    "level": r.get("level")}, mapped, t, source_id=uid, pointer=f"/{i}")
        else:
            b.mark(i, r, (), f"/{i}")
    return b


def codex(raw, source):
    if not isinstance(raw, list):
        raise ValueError("Codex expects rollout JSONL records")
    sid = next((r.get("payload", {}).get("id") for r in raw
                if r.get("type") == "session_meta" and isinstance(r.get("payload"), dict)), Path(source).stem)
    b = Builder("codex", source, sid)
    for i, r in enumerate(raw):
        typ = r.get("type")
        p = r.get("payload") or {}
        if not isinstance(p, dict):
            b.mark(i, r, ["/type", "/timestamp"], f"/{i}")
            continue
        base = ["/type", "/timestamp"]
        t = r.get("timestamp")
        if typ == "session_meta":
            keys = ["id", "cwd", "originator", "cli_version", "model_provider"]
            payload = {k: p[k] for k in keys if k in p}
            b.emit(i, r, "metadata", "system", "Codex session", payload,
                   base + ["/payload/" + k for k in keys if k in p], t, pointer=f"/{i}")
        elif typ == "turn_context":
            keys = ["model", "cwd", "turn_id", "approval_policy"]
            b.emit(i, r, "state", "system", "turn_context",
                   {k: p[k] for k in keys if k in p},
                   base + ["/payload/" + k for k in keys if k in p], t, pointer=f"/{i}")
        elif typ == "response_item":
            itype = p.get("type")
            used = base + ["/payload/type"]
            if itype == "message":
                role = p.get("role", "assistant")
                if role not in ("assistant", "user", "system"):
                    role = "assistant"
                cont = p.get("content", [])
                blocks = content_blocks(cont)
                texts = [x.get("text", "") for x in blocks if isinstance(x, dict)]
                b.emit(i, r, "message", role, " ".join(texts), {"content": cont, "role": role},
                       used + ["/payload/role", "/payload/content"], t, pointer=f"/{i}")
            elif itype in ("function_call", "custom_tool_call"):
                cid = p.get("call_id") or p.get("id")
                args = p.get("arguments", p.get("input", ""))
                b.emit(i, r, "tool_call", "assistant", p.get("name", itype),
                       {"name": p.get("name"), "arguments": args, "item_type": itype},
                       used + ["/payload/name", "/payload/call_id",
                               "/payload/id", "/payload/arguments", "/payload/input"], t, cid, pointer=f"/{i}")
            elif itype in ("function_call_output", "custom_tool_call_output"):
                cid = p.get("call_id") or p.get("id")
                b.emit(i, r, "tool_result", "tool", p.get("output", ""),
                       {"output": p.get("output"), "item_type": itype},
                       used + ["/payload/call_id", "/payload/id", "/payload/output"], t, cid, pointer=f"/{i}")
            elif itype == "reasoning":
                b.emit(i, r, "thought", "assistant", p.get("summary", "[reasoning item]"),
                       {"summary": p.get("summary")}, used + ["/payload/summary"], t, pointer=f"/{i}")
            else:
                b.mark(i, r, base + ["/payload/type"], f"/{i}")
        elif typ == "event_msg":
            subtype = p.get("type")
            if subtype == "token_count":
                b.emit(i, r, "metadata", "system", "token_count",
                       {"token_count": p.get("info")}, base + ["/payload/type", "/payload/info"],
                       t, pointer=f"/{i}")
            else:
                # These often duplicate response_item content (TUI display stream).
                b.mark(i, r, base + ["/payload/type"], f"/{i}")
        else:
            b.mark(i, r, base, f"/{i}")
    return b


def openhands(raw, source):
    if isinstance(raw, dict):
        rows = []
        for key in ("before", "after", "events"):
            for j, row in enumerate(raw.get(key) or []):
                rows.append((row, f"/{key}/{j}"))
        if not rows:
            rows = [(raw, "/")]
    elif isinstance(raw, list):
        rows = [(x, f"/{i}") for i, x in enumerate(raw)]
    else:
        raise ValueError("OpenHands expects events or socket capture")
    b = Builder("openhands", source, Path(source).stem)
    observed_ids = set()
    for i, (row, path) in enumerate(rows):
        ev = row.get("event", row)
        if not isinstance(ev, dict):
            b.mark(i, row, (), path)
            continue
        eid = ev.get("id")
        if eid and eid in observed_ids:
            continue
        if eid:
            observed_ids.add(eid)
        kind = ev.get("kind", "")
        t = ev.get("timestamp")
        pre = "/event" if "event" in row else ""
        base = [pre + "/" + k for k in ("id", "timestamp", "source", "kind") if k in ev]
        base += ["/seq", "/type"] if "event" in row else []
        if kind == "MessageEvent":
            b.emit(i, row, "message",
                   "user" if ev.get("source") == "user" else "assistant",
                   ev.get("llm_message", ev.get("message", {})),
                   {"llm_message": ev.get("llm_message"), "message": ev.get("message")},
                   base + [pre + "/llm_message", pre + "/message"], t,
                   source_id=eid, pointer=path)
        elif kind == "ActionEvent":
            action = ev.get("action", {})
            cid = ev.get("tool_call_id")
            b.emit(i, row, "tool_call", "agent", ev.get("tool_name", kind),
                   {"name": ev.get("tool_name"), "action": action, "thought": ev.get("thought")},
                   base + [pre + "/tool_name", pre + "/tool_call_id",
                           pre + "/action", pre + "/thought"], t, cid, source_id=eid, pointer=path)
        elif kind == "ObservationEvent":
            b.emit(i, row, "tool_result", "environment", ev.get("observation", {}),
                   {"observation": ev.get("observation"), "tool_name": ev.get("tool_name")},
                   base + [pre + "/observation", pre + "/tool_name", pre + "/tool_call_id"],
                   t, ev.get("tool_call_id"), source_id=eid, pointer=path)
        elif kind in ("AgentErrorEvent", "ErrorEvent"):
            b.emit(i, row, "error", "agent", ev.get("error", kind),
                   {"error": ev.get("error")}, base + [pre + "/error"], t,
                   source_id=eid, pointer=path)
        else:
            # Preserve a meaningful event-level marker, audit the opaque state as omitted.
            b.emit(i, row, "state", "system", kind or row.get("type", "event"),
                   {"kind": kind, "stream_type": row.get("type"), "sequence": row.get("seq")},
                   base, t, source_id=eid, pointer=path)
    return b


def langgraph(raw, source):
    if isinstance(raw, dict):
        rows = raw.get("history", [raw])
        session = raw.get("thread_id") or Path(source).stem
    else:
        rows = raw
        session = Path(source).stem
    if not isinstance(rows, list):
        raise ValueError("LangGraph expects JSON snapshot list or debug events")
    b = Builder("langgraph", source, session)
    for i, row in enumerate(rows):
        if row.get("type") in ("checkpoint", "task", "task_result"):
            p = row.get("payload") or {}
            typ = row["type"]
            if typ == "checkpoint":
                b.emit(i, row, "checkpoint", "system", "checkpoint",
                       {"values": p.get("values"), "next": p.get("next"), "tasks": p.get("tasks"),
                        "config": p.get("config"), "metadata": p.get("metadata")},
                       ["/type", "/timestamp", "/step", "/payload/values", "/payload/next",
                        "/payload/tasks", "/payload/config", "/payload/metadata"],
                       row.get("timestamp"), pointer=f"/{i}")
            else:
                b.emit(i, row, "state", "agent", typ,
                       {"task": p}, ["/type", "/timestamp", "/step", "/payload"],
                       row.get("timestamp"), pointer=f"/{i}")
        else:
            conf = row.get("config") or {}
            pconf = row.get("parent_config")
            b.emit(i, row, "checkpoint", "system", "next: " + str(row.get("next")),
                   {"values": row.get("values"), "next": row.get("next"),
                    "tasks": row.get("tasks"), "config": conf, "metadata": row.get("metadata"),
                    "parent_config": pconf},
                   ["/values", "/next", "/tasks", "/config", "/metadata", "/parent_config", "/created_at"],
                   row.get("created_at"), source_id=(conf.get("configurable") or {}).get("checkpoint_id"),
                   pointer=f"/{i}")
    return b


def swe_agent(raw, source):
    if not isinstance(raw, dict):
        raise ValueError("SWE-agent expects .traj JSON object")
    steps = raw.get("trajectory")
    history = raw.get("history")
    if not isinstance(steps, list) and not isinstance(history, list):
        raise ValueError("SWE-agent expects trajectory[] or history[]")
    sid = raw.get("instance_id", Path(source).stem)
    b = Builder("swe-agent", source, sid)
    if "info" in raw:
        b.warnings.append("root.info kept only in original .traj; no score inferred")

    if isinstance(steps, list):
        if isinstance(history, list):
            b.warnings.append("root.history not projected: may duplicate trajectory steps")
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            if step.get("thought") is not None:
                b.emit(i, step, "thought", "assistant", step.get("thought"),
                       {"text": step.get("thought"), "response": step.get("response")},
                       ["/thought", "/response"], step.get("timestamp"), pointer=f"/trajectory/{i}")
            if step.get("action") is not None:
                cid = f"swe-step-{i}"
                b.emit(i, step, "tool_call", "agent", step["action"],
                       {"name": "shell", "command": step["action"]}, ["/action"], step.get("timestamp"),
                       cid, pointer=f"/trajectory/{i}")
                if step.get("observation") is not None:
                    b.emit(i, step, "tool_result", "environment", step["observation"],
                           {"content": step["observation"]}, ["/observation"], step.get("timestamp"),
                           cid, pointer=f"/trajectory/{i}")
            b.mark(i, step, ["/timestamp"] if "timestamp" in step else [], f"/trajectory/{i}")
        return b

    # SWE-agent demonstration exports can have history[] but no trajectory[].
    # In this form assistant rows carry real tool_calls IDs, and tool rows
    # carry the corresponding tool_call_ids. Preserve these IDs rather than
    # synthesizing per-step IDs when they exist.
    for i, row in enumerate(history):
        if not isinstance(row, dict):
            continue
        role = row.get("role", "")
        root_pointer = f"/history/{i}"
        used = ["/role", "/message_type", "/agent"]
        when = row.get("timestamp")
        metadata = {"agent": row.get("agent"), "message_type": row.get("message_type")}
        if role in ("system", "user"):
            b.emit(i, row, "message", role, row.get("content", ""),
                   {"content": row.get("content"), **metadata},
                   used + ["/content"], when, pointer=root_pointer)
        elif role == "assistant":
            if "thought" in row:
                b.emit(i, row, "thought", "assistant", row["thought"],
                       {"text": row["thought"], "content": row.get("content"), **metadata},
                       used + ["/thought", "/content"], when, pointer=root_pointer)
            elif "content" in row:
                b.emit(i, row, "message", "assistant", row["content"],
                       {"content": row["content"], **metadata},
                       used + ["/content"], when, pointer=root_pointer)
            calls = row.get("tool_calls") or []
            if calls:
                for j, tool in enumerate(calls):
                    fn = tool.get("function") or {}
                    cid = tool.get("id", f"swe-history-{i}-{j}")
                    b.emit(i, row, "tool_call", "agent", fn.get("name", row.get("action", "tool")),
                           {"name": fn.get("name"), "arguments": fn.get("arguments"),
                            "action": row.get("action"), "tool_call": tool, **metadata},
                           used + [f"/tool_calls/{j}", "/action"], when, cid, pointer=root_pointer)
            elif "action" in row:
                cid = f"swe-history-{i}"
                b.emit(i, row, "tool_call", "agent", row["action"],
                       {"name": "shell", "command": row["action"], **metadata},
                       used + ["/action"], when, cid, pointer=root_pointer)
        elif role == "tool":
            ids = row.get("tool_call_ids") or []
            if not ids:
                b.warnings.append("history row " + str(i) + ": tool result without tool_call_ids")
            for cid in ids:
                b.emit(i, row, "tool_result", "tool", row.get("content", ""),
                       {"content": row.get("content"), **metadata},
                       used + ["/content", "/tool_call_ids"], when, cid, pointer=root_pointer)
        else:
            b.mark(i, row, (), root_pointer)
        b.mark(i, row, ["/timestamp"] if when else [], root_pointer)
    return b


PARSERS = {"claude-code": claude, "codex": codex, "openhands": openhands,
           "langgraph": langgraph, "swe-agent": swe_agent}


def convert(path, fmt="auto"):
    raw = read_records(path)
    selected = detect(raw) if fmt == "auto" else fmt
    if selected not in PARSERS:
        raise ValueError(f"Unknown format {selected!r}; choose one of {FORMATS}")
    b = PARSERS[selected](raw, path)
    return b.result(), b.audit()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(description="Native Agent trajectory -> canonical events + field-loss report")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("convert", help="Convert a source JSON/JSONL/.traj")
    c.add_argument("input")
    c.add_argument("--format", choices=("auto",) + FORMATS, default="auto")
    c.add_argument("--out", required=True)
    c.add_argument("--report", required=True)
    batch = sub.add_parser("batch", help="Convert five native files for the static viewer")
    batch.add_argument("inputs", nargs="+")
    batch.add_argument("--outdir", default="demo/data")
    batch.add_argument("--format", choices=("auto",) + FORMATS, default="auto")
    args = p.parse_args(argv)
    if args.command == "convert":
        obj, report = convert(args.input, args.format)
        dump(args.out, obj)
        dump(args.report, report)
        print(f"{obj['source_format']}: {len(obj['events'])} events | mapped {report['mapped_leaf_count']} leaves; omitted {report['omitted_leaf_count']} leaves")
    elif args.command == "batch":
        outdir = Path(args.outdir)
        manifest = []
        for source in args.inputs:
            obj, report = convert(source, args.format)
            name = obj["source_format"] + "-" + Path(source).stem
            dump(outdir / (name + ".json"), {"trajectory": obj, "loss_report": report})
            manifest.append({"name": name, "file": name + ".json",
                             "format": obj["source_format"], "events": len(obj["events"]),
                             "mapped": report["mapped_leaf_count"],
                             "omitted": report["omitted_leaf_count"]})
        dump(outdir / "manifest.json", manifest)
        print(f"Wrote {len(manifest)} viewer datasets to {outdir}")


if __name__ == "__main__":
    main()
