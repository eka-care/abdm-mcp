import time
from state.store import FlowStateStore


class InMemoryFlowStateStore(FlowStateStore):
    def __init__(self):
        # {session_id: {data: dict, expires_at: float}}
        self._store: dict = {}

    async def get(self, session_id: str) -> dict | None:
        entry = self._store.get(session_id)
        if entry is None:
            return None
        if time.time() > entry["expires_at"]:
            del self._store[session_id]
            return None
        return entry["data"]

    async def set(self, session_id: str, state: dict, ttl: int) -> None:
        self._cleanup_expired()
        self._store[session_id] = {
            "data": state,
            "expires_at": time.time() + ttl,
        }

    async def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._store.items() if v["expires_at"] < now]
        for k in expired:
            del self._store[k]
