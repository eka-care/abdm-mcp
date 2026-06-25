from state.store import FlowStateStore
from state.flow_rules import FLOW_RULES, SESSION_TTL


class FlowValidator:
    def __init__(self, store: FlowStateStore):
        self._store = store

    async def validate_and_record(self, session_id: str, tool_name: str) -> None:
        if tool_name not in FLOW_RULES:
            # standalone tool — always allowed, does not update flow state
            return

        required_predecessors = FLOW_RULES[tool_name]

        if required_predecessors is None:
            # entry point — always allowed, resets flow state
            await self._store.set(session_id, {"last_tool": tool_name}, ttl=SESSION_TTL)
            return

        state = await self._store.get(session_id)
        last_tool = state["last_tool"] if state else None

        if last_tool not in required_predecessors:
            expected = " or ".join(f"`{t}`" for t in required_predecessors)
            raise ValueError(
                f"`{tool_name}` cannot be called after `{last_tool}`. "
                f"Expected {expected} to be called first."
            )

        await self._store.set(session_id, {"last_tool": tool_name}, ttl=SESSION_TTL)
