#!/usr/bin/env python3
"""Generate real LangGraph runtime checkpoint history; requires pip install langgraph."""
import argparse
import json
from typing import TypedDict
from pathlib import Path
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

class State(TypedDict):
    count: int
    log: list[str]

def step(s: State) -> State:
    return {"count": s["count"] + 1, "log": s["log"] + ["step executed"]}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="fixtures/real/langgraph.json")
    args = p.parse_args()
    g = StateGraph(State)
    g.add_node("increment", step)
    g.add_edge(START, "increment")
    g.add_edge("increment", END)
    graph = g.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "trajlab-langgraph-real"}}
    graph.invoke({"count": 0, "log": []}, config)
    history = []
    for snap in graph.get_state_history(config):
        history.append({
            "values": snap.values, "next": list(snap.next),
            "config": snap.config, "metadata": snap.metadata,
            "created_at": snap.created_at, "parent_config": snap.parent_config,
            "tasks": [{"id": t.id, "name": t.name, "path": list(t.path),
                       "error": str(t.error) if t.error else None} for t in snap.tasks]
        })
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"thread_id": "trajlab-langgraph-real", "history": history},
                               indent=2, default=str) + "\n")
    print(f"Generated {len(history)} genuine StateSnapshots -> {dest}")

if __name__ == "__main__":
    main()
