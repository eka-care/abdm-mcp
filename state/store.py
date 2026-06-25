from abc import ABC, abstractmethod


class FlowStateStore(ABC):
    @abstractmethod
    async def get(self, session_id: str) -> dict | None: ...

    @abstractmethod
    async def set(self, session_id: str, state: dict, ttl: int) -> None: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...
