"""Seed a minimal LangGraph run for integration tests.

Usage:
    python tests/fixtures/seed_graph.py --backend postgres|sqlite|redis
"""

from __future__ import annotations

import argparse
import os
import uuid


def build_graph(checkpointer, store=None):
    from langgraph.graph import END, START, MessagesState, StateGraph

    def echo(state: MessagesState):
        last = state["messages"][-1]
        from langchain_core.messages import AIMessage

        return {"messages": [AIMessage(content=f"echo: {getattr(last, 'content', last)}")]}

    builder = StateGraph(MessagesState)
    builder.add_node("echo", echo)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    return builder.compile(checkpointer=checkpointer, store=store)


def seed(backend: str) -> None:
    thread_id = "test-1"
    user_id = "user-test-1"
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        }
    }

    if backend == "postgres":
        uri = os.environ.get(
            "POSTGRES_URI",
            "postgresql://langgraph:langgraph@localhost:5442/langgraph",
        )
        from langgraph.checkpoint.postgres import PostgresSaver
        from langgraph.store.postgres import PostgresStore

        with PostgresSaver.from_conn_string(uri) as cp, PostgresStore.from_conn_string(
            uri
        ) as store:
            cp.setup()
            store.setup()
            graph = build_graph(cp, store)
            from langchain_core.messages import HumanMessage

            graph.invoke({"messages": [HumanMessage(content="turn 1")]}, config)
            graph.invoke({"messages": [HumanMessage(content="turn 2")]}, config)
            store.put((user_id, "prefs"), "theme", {"value": "dark"})
    elif backend == "sqlite":
        from pathlib import Path

        path = Path(os.environ.get("SQLITE_PATH", "./test-checkpoints.db"))
        path.parent.mkdir(parents=True, exist_ok=True)
        from langgraph.checkpoint.sqlite import SqliteSaver

        with SqliteSaver.from_conn_string(str(path)) as cp:
            cp.setup()
            graph = build_graph(cp)
            from langchain_core.messages import HumanMessage

            graph.invoke({"messages": [HumanMessage(content="turn 1")]}, config)
            graph.invoke({"messages": [HumanMessage(content="turn 2")]}, config)
    elif backend == "redis":
        uri = os.environ.get("REDIS_URI", "redis://localhost:6379/0")
        from langgraph.checkpoint.redis import RedisSaver

        with RedisSaver.from_conn_string(uri) as cp:
            cp.setup()
            graph = build_graph(cp)
            from langchain_core.messages import HumanMessage

            graph.invoke({"messages": [HumanMessage(content="turn 1")]}, config)
            graph.invoke({"messages": [HumanMessage(content="turn 2")]}, config)
    else:
        raise ValueError(backend)

    print(f"Seeded backend={backend} thread_id={thread_id} user_id={user_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["postgres", "sqlite", "redis"], required=True)
    args = parser.parse_args()
    seed(args.backend)
