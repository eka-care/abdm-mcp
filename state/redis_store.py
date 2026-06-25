import json
import redis.asyncio as redis
from state.store import FlowStateStore

KEY_PREFIX = "mcp:session:"


class RedisFlowStateStore(FlowStateStore):
    def __init__(self, redis_url: str):
        self._client = redis.from_url(redis_url)

    async def get(self, session_id: str) -> dict | None:
        value = await self._client.get(f"{KEY_PREFIX}{session_id}")
        if value is None:
            return None
        return json.loads(value)

    async def set(self, session_id: str, state: dict, ttl: int) -> None:
        await self._client.setex(f"{KEY_PREFIX}{session_id}", ttl, json.dumps(state))

    async def delete(self, session_id: str) -> None:
        await self._client.delete(f"{KEY_PREFIX}{session_id}")
