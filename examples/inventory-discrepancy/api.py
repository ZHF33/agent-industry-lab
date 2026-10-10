"""Single-process local API; LangGraph checkpoints live in memory."""
import os
import secrets
import threading
import uuid
from typing import Literal
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from langgraph.types import Command
from graph_agent import build_graph

app = FastAPI(title="Inventory Discrepancy")
graph = build_graph()
lock = threading.Lock()


class Ticket(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
    case_id: str = Field(min_length=1, max_length=2000)
    sku: str = Field(min_length=1, max_length=2000)
    description: str = Field(min_length=1, max_length=2000)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=120)


def authorize(x_api_key: str = Header(default="")):
    expected = os.environ.get("INVENTORY_API_KEY", "")
    if not expected:
        raise HTTPException(503, "Configure INVENTORY_API_KEY")
    if not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(401, "Invalid API key")


def config(thread_id):
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": 16}


def response(thread_id):
    state = graph.get_state(config(thread_id))
    return {"thread_id": thread_id, "pending_review": bool(state.next), "result": state.values.get("result")}


@app.post("/triage", dependencies=[Depends(authorize)])
def triage(ticket: Ticket):
    thread_id = str(uuid.uuid4())
    # Reject concurrent work rather than queueing indefinitely in HTTP workers.
    if not lock.acquire(blocking=False):
        raise HTTPException(429, "Agent busy; retry later")
    try:
        graph.invoke({"ticket": ticket.model_dump()}, config(thread_id))
        return response(thread_id)
    except Exception as error:
        raise HTTPException(502, "Agent failed; no completed review") from error
    finally:
        lock.release()


@app.post("/threads/{thread_id}/review", dependencies=[Depends(authorize)])
def review(thread_id: uuid.UUID, decision: Review):
    if not lock.acquire(blocking=False):
        raise HTTPException(429, "Agent busy; retry later")
    try:
        key = str(thread_id)
        snapshot = graph.get_state(config(key))
        if not snapshot.values:
            raise HTTPException(404, "Unknown thread or server restarted")
        if snapshot.next != ("review",):
            raise HTTPException(409, "Thread is not awaiting review")
        graph.invoke(Command(resume=decision.model_dump()), config(key))
        return response(key)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(502, "Review failed") from error
    finally:
        lock.release()
