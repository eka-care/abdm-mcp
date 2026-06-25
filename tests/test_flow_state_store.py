import asyncio
import pytest
from state.memory import InMemoryFlowStateStore


@pytest.mark.asyncio
async def test_set_and_get():
    store = InMemoryFlowStateStore()
    await store.set("session1", {"last_tool": "init"}, ttl=60)
    result = await store.get("session1")
    assert result == {"last_tool": "init"}


@pytest.mark.asyncio
async def test_get_missing_returns_none():
    store = InMemoryFlowStateStore()
    result = await store.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_delete():
    store = InMemoryFlowStateStore()
    await store.set("session1", {"last_tool": "init"}, ttl=60)
    await store.delete("session1")
    result = await store.get("session1")
    assert result is None


@pytest.mark.asyncio
async def test_expired_entry_returns_none():
    import time
    store = InMemoryFlowStateStore()
    await store.set("session1", {"last_tool": "init"}, ttl=1)
    # manually expire it
    store._store["session1"]["expires_at"] = time.time() - 1
    result = await store.get("session1")
    assert result is None


@pytest.mark.asyncio
async def test_cleanup_removes_expired():
    import time
    store = InMemoryFlowStateStore()
    await store.set("session1", {"last_tool": "init"}, ttl=60)
    await store.set("session2", {"last_tool": "init"}, ttl=60)
    store._store["session1"]["expires_at"] = time.time() - 1
    store._cleanup_expired()
    assert "session1" not in store._store
    assert "session2" in store._store
