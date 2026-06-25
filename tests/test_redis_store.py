import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from state.redis_store import RedisFlowStateStore
import json


@pytest.mark.asyncio
async def test_set_and_get():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps({"last_tool": "init"})
    with patch("state.redis_store.redis.from_url", return_value=mock_redis):
        store = RedisFlowStateStore("redis://localhost:6379")
        await store.set("session1", {"last_tool": "init"}, ttl=60)
        mock_redis.setex.assert_called_once_with(
            "mcp:session:session1", 60, json.dumps({"last_tool": "init"})
        )
        result = await store.get("session1")
        assert result == {"last_tool": "init"}


@pytest.mark.asyncio
async def test_get_missing_returns_none():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    with patch("state.redis_store.redis.from_url", return_value=mock_redis):
        store = RedisFlowStateStore("redis://localhost:6379")
        result = await store.get("nonexistent")
        assert result is None


@pytest.mark.asyncio
async def test_delete():
    mock_redis = AsyncMock()
    with patch("state.redis_store.redis.from_url", return_value=mock_redis):
        store = RedisFlowStateStore("redis://localhost:6379")
        await store.delete("session1")
        mock_redis.delete.assert_called_once_with("mcp:session:session1")
