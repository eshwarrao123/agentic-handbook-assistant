"""Tests for durable SQLite checkpoint persistence and thread isolation (GR-014, GR-015, API-006, AR-012, AR-046)."""

import os
import uuid
import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.booking.service import get_booking_service
from app.graph.builder import build_graph


@pytest.fixture(autouse=True)
def reset_service():
    """Reset deterministic booking inventory before each test."""
    svc = get_booking_service()
    svc.reset()
    yield
    svc.reset()


@pytest.mark.asyncio
async def test_sqlite_persistence_across_process_restart(tmp_path):
    """GR-014 & AR-046: State survives process restart via a fresh checkpointer and graph on the same SQLite DB."""
    db_file = str(tmp_path / "checkpoints.sqlite")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # =========================================================================
    # PROCESS 1: User starts booking and provides name + email
    # =========================================================================
    async with AsyncSqliteSaver.from_conn_string(db_file) as cp1:
        await cp1.setup()
        graph1 = build_graph(checkpointer=cp1)

        # Turn 1: User provides name and email
        res1 = await graph1.ainvoke(
            {"messages": [HumanMessage(content="Schedule review for Dana Scully (dana.scully@example.com)")]},
            config=config,
        )

        assert res1["booking"]["status"] == "awaiting_slot"
        assert res1["booking"]["full_name"] == "Dana Scully"
        assert res1["booking"]["email"] == "dana.scully@example.com"
        assert len(res1["booking"]["offered_slots"]) == 3
        offered_ids = [s["slot_id"] for s in res1["booking"]["offered_slots"]]

    # Process 1 exits; saver and graph are destroyed. Connection pool is closed.

    # =========================================================================
    # PROCESS 2: Fresh checkpointer, fresh graph, same SQLite DB file
    # =========================================================================
    async with AsyncSqliteSaver.from_conn_string(db_file) as cp2:
        await cp2.setup()
        graph2 = build_graph(checkpointer=cp2)

        # Verify state recovery from SQLite
        recovered_state = await graph2.aget_state(config)
        assert bool(recovered_state and recovered_state.values) is True
        recovered_booking = recovered_state.values["booking"]
        assert recovered_booking["status"] == "awaiting_slot"
        assert recovered_booking["full_name"] == "Dana Scully"
        assert recovered_booking["email"] == "dana.scully@example.com"
        assert [s["slot_id"] for s in recovered_booking["offered_slots"]] == offered_ids

        # Turn 2: User completes booking on the restored thread
        res2 = await graph2.ainvoke(
            {"messages": [HumanMessage(content="Option 1")]},
            config=config,
        )

        assert res2["booking"]["status"] == "confirmed"
        assert res2["booking"]["booking_reference"] is not None
        assert res2["booking"]["booking_reference"].startswith("#REV-")
        assert res2["booking"]["full_name"] == "Dana Scully"
        assert res2["booking"]["email"] == "dana.scully@example.com"
        assert res2["booking"]["confirmed_slot"]["slot_id"] == offered_ids[0]

    # Process 2 exits.

    # =========================================================================
    # PROCESS 3: Final verification of confirmed state after second simulated restart
    # =========================================================================
    async with AsyncSqliteSaver.from_conn_string(db_file) as cp3:
        await cp3.setup()
        graph3 = build_graph(checkpointer=cp3)
        final_state = await graph3.aget_state(config)
        assert final_state.values["booking"]["status"] == "confirmed"
        assert final_state.values["booking"]["booking_reference"] == res2["booking"]["booking_reference"]


@pytest.mark.asyncio
async def test_sqlite_thread_isolation(tmp_path):
    """GR-015: Separate thread IDs on the same SQLite checkpointer remain strictly isolated."""
    db_file = str(tmp_path / "checkpoints.sqlite")
    thread_a = str(uuid.uuid4())
    thread_b = str(uuid.uuid4())
    config_a = {"configurable": {"thread_id": thread_a}}
    config_b = {"configurable": {"thread_id": thread_b}}

    async with AsyncSqliteSaver.from_conn_string(db_file) as cp:
        await cp.setup()
        graph = build_graph(checkpointer=cp)

        # Thread A: Initiates booking for Alice
        await graph.ainvoke(
            {"messages": [HumanMessage(content="Book review for Alice Cooper (alice@example.com)")]},
            config=config_a,
        )

        # Thread B: Asks a general handbook FAQ question
        res_b = await graph.ainvoke(
            {"messages": [HumanMessage(content="How often are performance reviews conducted according to the handbook?")]},
            config=config_b,
        )

        # Thread B assertions
        assert res_b["booking"]["status"] == "none"
        assert res_b["booking"]["full_name"] is None
        assert res_b["booking"]["email"] is None
        assert "conducted annually" in res_b["reply_parts"][0].lower()

        # Thread A assertions: completely unaffected by Thread B
        state_a = await graph.aget_state(config_a)
        assert state_a.values["booking"]["status"] == "awaiting_slot"
        assert state_a.values["booking"]["full_name"] == "Alice Cooper"
        assert state_a.values["booking"]["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_sqlite_wal_mode_and_schema(tmp_path):
    """Verify that AsyncSqliteSaver sets WAL journal mode and creates checkpoints/writes tables."""
    db_file = str(tmp_path / "checkpoints.sqlite")
    async with AsyncSqliteSaver.from_conn_string(db_file) as cp:
        await cp.setup()
        # Query SQLite sqlite_master to verify tables exist
        async with cp.conn.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
            tables = [row[0] for row in await cursor.fetchall()]
            assert "checkpoints" in tables
            assert "writes" in tables

        # Query journal mode
        async with cp.conn.execute("PRAGMA journal_mode") as cursor:
            row = await cursor.fetchone()
            assert row[0].lower() == "wal"
