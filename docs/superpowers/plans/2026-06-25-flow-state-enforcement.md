# Flow State Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce correct ABDM tool call sequencing per session so the LLM cannot call a verify tool without a preceding init, regardless of user instruction.

**Architecture:** A `FlowStateStore` abstraction with two implementations — `InMemoryFlowStateStore` for stdio (single session, Python dict) and `RedisFlowStateStore` for stateful HTTP (keyed by `mcp-session-id`). A `FlowValidator` reads the store before each tool call and writes to it after. Transport detection at startup injects the correct store. `stateless_http=True` is removed from HTTP transport so `mcp-session-id` is available.

**Tech Stack:** FastMCP 3.4.2, Python 3.11+, redis-py (optional, stateful HTTP only), existing tool files in `tools/m1/`

## Global Constraints

- Python 3.11+
- FastMCP >= 2.0.0
- No new required dependencies for stdio transport — Redis is optional, only needed for stateful HTTP
- Do not modify `clients/`, `services/`, or `tools/m1/models.py`
- Do not break existing tool function signatures
- `mcp-session-id` header is only available when `stateless_http=True` is NOT set

---

## File Structure

**New files:**
- `state/__init__.py` — empty
- `state/store.py` — `FlowStateStore` abstract base class
- `state/memory.py` — `InMemoryFlowStateStore` (dict + TTL cleanup)
- `state/redis_store.py` — `RedisFlowStateStore` (redis-py async)
- `state/flow_rules.py` — valid predecessor mapping per tool name
- `state/validator.py` — `FlowValidator`: reads store, validates, writes store
- `tests/test_flow_validator.py` — unit tests for validator logic

**Modified files:**
- `server.py` — remove `stateless_http=True`, detect transport, inject store into validator, pass validator to register functions
- `tools/m1/abha_enrollment_tools.py` — call validator before/after each tool
- `tools/m1/abha_verification_tools.py` — call validator before/after each tool
- `tools/m1/abha_address_verification_tools.py` — call validator before/after each tool
- `tools/m1/find_abha_tools.py` — call validator before/after each tool
- `requirements.txt` — add `redis>=5.0.0` as optional comment

---

### Task 1: FlowStateStore abstraction + InMemoryFlowStateStore

**Files:**
- Create: `state/__init__.py`
- Create: `state/store.py`
- Create: `state/memory.py`
- Test: `tests/test_flow_state_store.py`

**Interfaces:**
- Produces:
  - `FlowStateStore` with `async get(session_id: str) -> dict | None` and `async set(session_id: str, state: dict, ttl: int) -> None` and `async delete(session_id: str) -> None`
  - `InMemoryFlowStateStore(FlowStateStore)` — concrete implementation

- [ ] **Step 1: Create `state/__init__.py`**

```python
```
(empty file)

- [ ] **Step 2: Write failing tests**

Create `tests/test_flow_state_store.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd D:\ABDM\abdm-mcp && .venv\Scripts\python.exe -m pytest tests/test_flow_state_store.py -v
```
Expected: ImportError — `state.memory` not found

- [ ] **Step 4: Create `state/store.py`**

```python
from abc import ABC, abstractmethod


class FlowStateStore(ABC):
    @abstractmethod
    async def get(self, session_id: str) -> dict | None: ...

    @abstractmethod
    async def set(self, session_id: str, state: dict, ttl: int) -> None: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...
```

- [ ] **Step 5: Create `state/memory.py`**

```python
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
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd D:\ABDM\abdm-mcp && .venv\Scripts\python.exe -m pytest tests/test_flow_state_store.py -v
```
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add state/__init__.py state/store.py state/memory.py tests/test_flow_state_store.py
git commit -m "feat: add FlowStateStore abstraction and InMemoryFlowStateStore"
```

---

### Task 2: RedisFlowStateStore

**Files:**
- Create: `state/redis_store.py`
- Modify: `requirements.txt`
- Test: `tests/test_redis_store.py`

**Interfaces:**
- Consumes: `FlowStateStore` from `state/store.py`
- Produces: `RedisFlowStateStore(FlowStateStore)` — takes `redis_url: str` in constructor

- [ ] **Step 1: Add redis to requirements.txt**

```
fastmcp>=2.0.0
httpx>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
redis>=5.0.0  # required for stateful HTTP transport only
```

- [ ] **Step 2: Install redis**

```bash
cd D:\ABDM\abdm-mcp && .venv\Scripts\pip install redis>=5.0.0
```

- [ ] **Step 3: Write failing tests**

Create `tests/test_redis_store.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from state.redis_store import RedisFlowStateStore
import json


@pytest.mark.asyncio
async def test_set_and_get():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps({"last_tool": "init"})
    with patch("state.redis_store.redis.asyncio.from_url", return_value=mock_redis):
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
    with patch("state.redis_store.redis.asyncio.from_url", return_value=mock_redis):
        store = RedisFlowStateStore("redis://localhost:6379")
        result = await store.get("nonexistent")
        assert result is None


@pytest.mark.asyncio
async def test_delete():
    mock_redis = AsyncMock()
    with patch("state.redis_store.redis.asyncio.from_url", return_value=mock_redis):
        store = RedisFlowStateStore("redis://localhost:6379")
        await store.delete("session1")
        mock_redis.delete.assert_called_once_with("mcp:session:session1")
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd D:\ABDM\abdm-mcp && .venv\Scripts\python.exe -m pytest tests/test_redis_store.py -v
```
Expected: ImportError — `state.redis_store` not found

- [ ] **Step 5: Create `state/redis_store.py`**

```python
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
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd D:\ABDM\abdm-mcp && .venv\Scripts\python.exe -m pytest tests/test_redis_store.py -v
```
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add state/redis_store.py requirements.txt tests/test_redis_store.py
git commit -m "feat: add RedisFlowStateStore"
```

---

### Task 3: Flow rules + FlowValidator

**Files:**
- Create: `state/flow_rules.py`
- Create: `state/validator.py`
- Test: `tests/test_flow_validator.py`

**Interfaces:**
- Consumes: `FlowStateStore` from `state/store.py`
- Produces:
  - `FLOW_RULES: dict[str, list[str] | None]` — maps tool name to valid predecessor tool names (None = no predecessor required)
  - `FlowValidator` with `async validate_and_record(session_id: str, tool_name: str) -> None` — raises `ValueError` with message if invalid, writes new state on success
  - `SESSION_TTL: int = 600`

- [ ] **Step 1: Write failing tests**

Create `tests/test_flow_validator.py`:

```python
import pytest
from state.memory import InMemoryFlowStateStore
from state.validator import FlowValidator


@pytest.mark.asyncio
async def test_entry_tool_allowed_with_no_prior_state():
    store = InMemoryFlowStateStore()
    validator = FlowValidator(store)
    # aadhaar_enrollment_init has no required predecessor
    await validator.validate_and_record("session1", "aadhaar_enrollment_init")
    state = await store.get("session1")
    assert state["last_tool"] == "aadhaar_enrollment_init"


@pytest.mark.asyncio
async def test_sequential_tool_allowed_after_correct_predecessor():
    store = InMemoryFlowStateStore()
    validator = FlowValidator(store)
    await validator.validate_and_record("session1", "aadhaar_enrollment_init")
    await validator.validate_and_record("session1", "aadhaar_enrollment_verify_otp")
    state = await store.get("session1")
    assert state["last_tool"] == "aadhaar_enrollment_verify_otp"


@pytest.mark.asyncio
async def test_sequential_tool_rejected_without_predecessor():
    store = InMemoryFlowStateStore()
    validator = FlowValidator(store)
    with pytest.raises(ValueError, match="aadhaar_enrollment_init"):
        await validator.validate_and_record("session1", "aadhaar_enrollment_verify_otp")


@pytest.mark.asyncio
async def test_wrong_flow_tool_rejected():
    store = InMemoryFlowStateStore()
    validator = FlowValidator(store)
    await validator.validate_and_record("session1", "aadhaar_enrollment_init")
    with pytest.raises(ValueError, match="find_abha_init"):
        await validator.validate_and_record("session1", "find_abha_verify")


@pytest.mark.asyncio
async def test_entry_tool_resets_flow():
    store = InMemoryFlowStateStore()
    validator = FlowValidator(store)
    await validator.validate_and_record("session1", "search_abha")
    await validator.validate_and_record("session1", "find_abha_init")
    # starting a new flow resets state
    await validator.validate_and_record("session1", "aadhaar_enrollment_init")
    state = await store.get("session1")
    assert state["last_tool"] == "aadhaar_enrollment_init"


@pytest.mark.asyncio
async def test_standalone_tool_always_allowed():
    store = InMemoryFlowStateStore()
    validator = FlowValidator(store)
    # get_abha_profile has no predecessor requirement and does not affect flow state
    await validator.validate_and_record("session1", "aadhaar_enrollment_init")
    await validator.validate_and_record("session1", "get_abha_profile")
    # flow state unchanged after standalone tool
    state = await store.get("session1")
    assert state["last_tool"] == "aadhaar_enrollment_init"


@pytest.mark.asyncio
async def test_verify_abha_confirm_can_be_called_twice():
    store = InMemoryFlowStateStore()
    validator = FlowValidator(store)
    await validator.validate_and_record("session1", "verify_abha_init")
    await validator.validate_and_record("session1", "verify_abha_confirm")
    # second call (account selection sub-step) also valid
    await validator.validate_and_record("session1", "verify_abha_confirm")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd D:\ABDM\abdm-mcp && .venv\Scripts\python.exe -m pytest tests/test_flow_validator.py -v
```
Expected: ImportError — `state.validator` not found

- [ ] **Step 3: Create `state/flow_rules.py`**

```python
# Maps each tool to the set of valid preceding tools.
# None means the tool can be called at any time (entry point or standalone).
# Tools not in this dict are standalone — they don't affect flow state.

FLOW_RULES: dict[str, list[str] | None] = {
    # Aadhaar enrollment
    "aadhaar_enrollment_init": None,
    "aadhaar_enrollment_verify_otp": ["aadhaar_enrollment_init"],
    "aadhaar_enrollment_verify_mobile_otp": ["aadhaar_enrollment_verify_otp"],
    "aadhaar_enrollment_suggest_address": [
        "aadhaar_enrollment_verify_otp",
        "aadhaar_enrollment_verify_mobile_otp",
    ],
    "aadhaar_enrollment_create_address": ["aadhaar_enrollment_suggest_address"],

    # Biometric enrollment — standalone, no predecessor
    "enroll_abha_by_biometric": None,

    # ABHA verification
    "verify_abha_init": None,
    "verify_abha_confirm": ["verify_abha_init", "verify_abha_confirm"],

    # ABHA address verification
    "search_abha_address_auth_methods": None,
    "abha_address_verification_init": ["search_abha_address_auth_methods"],
    "abha_address_verification_confirm": ["abha_address_verification_init"],

    # Find ABHA
    "search_abha": None,
    "find_abha_init": ["search_abha"],
    "find_abha_verify": ["find_abha_init"],
}

# Tools not in FLOW_RULES are standalone — always allowed, don't update flow state.
# e.g. get_abha_profile, get_abha_qr, get_abha_card, get_session, invalidate_session

SESSION_TTL = 600  # 10 minutes
```

- [ ] **Step 4: Create `state/validator.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd D:\ABDM\abdm-mcp && .venv\Scripts\python.exe -m pytest tests/test_flow_validator.py -v
```
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add state/flow_rules.py state/validator.py tests/test_flow_validator.py
git commit -m "feat: add flow rules and FlowValidator"
```

---

### Task 4: Server wiring — transport detection + store injection

**Files:**
- Modify: `server.py`
- Modify: `config/settings.py`

**Interfaces:**
- Consumes: `InMemoryFlowStateStore` from `state/memory.py`, `RedisFlowStateStore` from `state/redis_store.py`, `FlowValidator` from `state/validator.py`
- Produces: `FlowValidator` instance passed to each `register_*` function as second argument

- [ ] **Step 1: Add optional redis_url to settings**

In `config/settings.py`, add one field:

```python
redis_url: str = Field(default="")
```

Full updated `config/settings.py`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ABDM_", extra="ignore")
    gateway_base_url: str = Field(default="http://localhost:8080")
    gateway_timeout: int = Field(default=30)
    facility_id: str = Field(default="")
    gateway_api_key: str = Field(default="")
    redis_url: str = Field(default="")


settings = Settings()
```

- [ ] **Step 2: Update `server.py`**

```python
import argparse
import logging
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from config.settings import settings
from state.memory import InMemoryFlowStateStore
from state.validator import FlowValidator
from tools.m1.abha_enrollment_tools import register_abha_enrollment_tools
from tools.m1.abha_verification_tools import register_abha_verification_tools
from tools.m1.abha_address_verification_tools import register_abha_address_verification_tools
from tools.m1.find_abha_tools import register_find_abha_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_validator(transport: str) -> FlowValidator:
    if transport == "http" and settings.redis_url:
        from state.redis_store import RedisFlowStateStore
        logger.info("Flow state: Redis (%s)", settings.redis_url)
        return FlowValidator(RedisFlowStateStore(settings.redis_url))
    logger.info("Flow state: in-memory (single session)")
    return FlowValidator(InMemoryFlowStateStore())


def create_mcp_server(validator: FlowValidator) -> FastMCP:
    mcp = FastMCP(
        name="ABDM Compliance Gateway",
        instructions="""
            MCP server for the ABDM Compliance Gateway.
            Provides tools for managing ABHA (Ayushman Bharat Health Account) for patients.

            Available flows:
            - ABHA Enrollment: Create a new ABHA using Aadhaar OTP or biometric.
            - ABHA Verification: Verify an existing ABHA number using OTP.
            - ABHA Address Verification: Verify an ABHA address (e.g. patient@abdm).
            - Find ABHA: Search and retrieve an ABHA profile by mobile number.
            - Profile and Assets: Fetch ABHA profile, QR code, and health card.
            - Session: Manage active ABDM sessions.

            Production deployments must use stateful HTTP or stdio transport.
            Stateless HTTP does not support flow enforcement.
        """
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    @mcp.custom_route("/token", methods=["POST"])
    async def token(request: Request) -> JSONResponse:
        return JSONResponse({"access_token": "dummy", "token_type": "bearer", "expires_in": 3600})

    register_abha_enrollment_tools(mcp, validator)
    register_abha_verification_tools(mcp, validator)
    register_abha_address_verification_tools(mcp, validator)
    register_find_abha_tools(mcp, validator)

    return mcp


def main():
    parser = argparse.ArgumentParser(description="ABDM MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="http")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()

    logger.info("Starting ABDM MCP Server (%s transport)", args.transport)
    validator = _build_validator(args.transport)
    mcp = create_mcp_server(validator)

    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify server starts without error**

```bash
cd D:\ABDM\abdm-mcp && .venv\Scripts\python.exe server.py --transport stdio
```
Expected: starts without ImportError (Ctrl+C to stop)

- [ ] **Step 4: Commit**

```bash
git add server.py config/settings.py
git commit -m "feat: wire transport-aware FlowValidator into server"
```

---

### Task 5: Integrate FlowValidator into tool files

**Files:**
- Modify: `tools/m1/abha_enrollment_tools.py`
- Modify: `tools/m1/abha_verification_tools.py`
- Modify: `tools/m1/abha_address_verification_tools.py`
- Modify: `tools/m1/find_abha_tools.py`

**Interfaces:**
- Consumes: `FlowValidator.validate_and_record(session_id: str, tool_name: str)` from `state/validator.py`
- Each `register_*` function signature changes from `(mcp: FastMCP)` to `(mcp: FastMCP, validator: FlowValidator)`

**Note on session_id for stdio:** stdio has one session per process. Use the constant `"default"` as the session_id — there is no `mcp-session-id` header in stdio. For stateful HTTP, the `mcp-session-id` is read from the FastMCP context. FastMCP exposes request metadata via `ctx: Context` — access it as `ctx.meta.get("mcp-session-id", "default")` if available, otherwise fall back to `"default"`.

- [ ] **Step 1: Update `tools/m1/abha_enrollment_tools.py`**

```python
import logging
from typing import Any, Dict
from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.abha_enrollment_service import AbhaEnrollmentService
from state.validator import FlowValidator
from tools.m1.models import (
    AadhaarEnrollmentInitInput,
    AadhaarEnrollmentVerifyOTPInput,
    AadhaarEnrollmentVerifyMobileOTPInput,
    AadhaarEnrollmentSuggestAddressInput,
    AadhaarEnrollmentCreateAddressInput,
    EnrollABHAByBiometricInput,
)

logger = logging.getLogger(__name__)

_client = ABDMGatewayClient()
_service = AbhaEnrollmentService(_client)


def _session_id(ctx: Context) -> str:
    try:
        return ctx.meta.get("mcp-session-id", "default") or "default"
    except Exception:
        return "default"


def register_abha_enrollment_tools(mcp: FastMCP, validator: FlowValidator) -> None:

    logger.info("Registering ABHA enrollment tools...")

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_init(request: AadhaarEnrollmentInitInput, ctx: Context) -> Dict[str, Any]:
        """
        Sends an OTP to the mobile number linked to the patient's Aadhaar.

        Accepts: aadhaar_number (12-digit string)
        Returns: txn_id

        The patient will receive an OTP on their Aadhaar-linked mobile sent by this tool. Ask the patient for that OTP and their 10-digit mobile number.
        Follow-up: pass the txn_id returned by this tool, the OTP sent by this tool that the patient provides, and their mobile number to aadhaar_enrollment_verify_otp.

        Do not call if an enrollment session is already in progress for this patient — it will invalidate the existing txn_id.
        """
        await validator.validate_and_record(_session_id(ctx), "aadhaar_enrollment_init")
        logger.info(f"aadhaar_enrollment_init called: aadhaar_number={request.aadhaar_number}")
        return await _service.aadhaar_enrollment_init(request.aadhaar_number)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_verify_otp(request: AadhaarEnrollmentVerifyOTPInput, ctx: Context) -> Dict[str, Any]:
        """
        Verifies the OTP sent by aadhaar_enrollment_init and advances the enrollment state.

        Accepts:
        - txn_id returned by aadhaar_enrollment_init
        - otp sent by aadhaar_enrollment_init that the patient received on their Aadhaar-linked mobile
        - mobile (10-digit, provided by the patient)
        Returns: txn_id, skip_state

        Follow-up depends on skip_state:
        - confirm_mobile_otp → this tool will trigger a new OTP to the patient's mobile, ask the patient for that OTP, pass the txn_id returned by this tool and that OTP to aadhaar_enrollment_verify_mobile_otp
        - abha_create        → pass the txn_id returned by this tool to aadhaar_enrollment_suggest_address
        - abha_end           → enrollment complete, ABHA profile is in this response

        Do not call without the txn_id from aadhaar_enrollment_init.
        Do not call again after skip_state = abha_end.
        """
        await validator.validate_and_record(_session_id(ctx), "aadhaar_enrollment_verify_otp")
        return await _service.aadhaar_enrollment_verify_otp(request.txn_id, request.otp, request.mobile)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_verify_mobile_otp(request: AadhaarEnrollmentVerifyMobileOTPInput, ctx: Context) -> Dict[str, Any]:
        """
        Verifies the OTP sent to the patient's mobile by aadhaar_enrollment_verify_otp as a secondary confirmation step.

        Accepts:
        - txn_id returned by aadhaar_enrollment_verify_otp
        - otp sent to the patient's mobile when aadhaar_enrollment_verify_otp returned skip_state = confirm_mobile_otp
        Returns: txn_id, skip_state

        Follow-up depends on skip_state:
        - abha_create → pass the txn_id returned by this tool to aadhaar_enrollment_suggest_address
        - abha_end    → enrollment complete, ABHA profile is in this response

        Do not call unless aadhaar_enrollment_verify_otp returned skip_state = confirm_mobile_otp.
        Do not use the txn_id from aadhaar_enrollment_init — it must be the txn_id from aadhaar_enrollment_verify_otp.
        """
        await validator.validate_and_record(_session_id(ctx), "aadhaar_enrollment_verify_mobile_otp")
        return await _service.aadhaar_enrollment_verify_mobile_otp(request.txn_id, request.otp)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def aadhaar_enrollment_suggest_address(request: AadhaarEnrollmentSuggestAddressInput, ctx: Context) -> Dict[str, Any]:
        """
        Returns a list of available ABHA address suggestions derived from the patient's Aadhaar data.

        Accepts:
        - txn_id returned by aadhaar_enrollment_verify_otp or aadhaar_enrollment_verify_mobile_otp (whichever was the last step that returned skip_state = abha_create)
        - user_detail (optional: name, dob — improves suggestion relevance)
        Returns: list of suggested ABHA addresses, txn_id

        Present the suggestions to the patient and ask them to choose one.
        Follow-up: pass the txn_id returned by this tool and the address the patient chose to aadhaar_enrollment_create_address.

        Do not call unless the previous step returned skip_state = abha_create.
        Do not use the txn_id from aadhaar_enrollment_init directly.
        """
        await validator.validate_and_record(_session_id(ctx), "aadhaar_enrollment_suggest_address")
        return await _service.aadhaar_enrollment_suggest_address(request.txn_id, request.user_detail.model_dump())

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_create_address(request: AadhaarEnrollmentCreateAddressInput, ctx: Context) -> Dict[str, Any]:
        """
        Creates the ABHA address the patient selected from the suggestions returned by aadhaar_enrollment_suggest_address, completing enrollment.

        Accepts:
        - txn_id returned by aadhaar_enrollment_suggest_address
        - abha_address chosen by the patient from the list returned by aadhaar_enrollment_suggest_address (without @abdm suffix)
        Returns: complete ABHA profile

        Do not pass an address not returned by aadhaar_enrollment_suggest_address — ABDM will reject it.
        Do not include the @abdm suffix in abha_address.
        Do not call without the txn_id from aadhaar_enrollment_suggest_address.
        """
        await validator.validate_and_record(_session_id(ctx), "aadhaar_enrollment_create_address")
        return await _service.aadhaar_enrollment_create_address(request.txn_id, request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def enroll_abha_by_biometric(request: EnrollABHAByBiometricInput, ctx: Context) -> Dict[str, Any]:
        """
        Enrolls a patient for ABHA in a single step using a biometric PID block captured from a certified device.

        Accepts: aadhaar_number (12-digit), pid (PID block from biometric device), mobile_number (10-digit)
        Returns: complete ABHA profile

        Do not use if no certified biometric device is present — use the Aadhaar OTP flow instead.
        Do not pass a manually constructed or mock PID block — ABDM validates the device signature.
        """
        await validator.validate_and_record(_session_id(ctx), "enroll_abha_by_biometric")
        return await _service.enroll_abha_by_biometric(request.aadhaar_number, request.pid, request.mobile_number)
```

- [ ] **Step 2: Update `tools/m1/abha_verification_tools.py`**

```python
from typing import Any, Dict
from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.abha_verification_service import AbhaVerificationService
from state.validator import FlowValidator
from tools.m1.models import VerifyABHAInitInput, VerifyABHAConfirmInput

_client = ABDMGatewayClient()
_service = AbhaVerificationService(_client)


def _session_id(ctx: Context) -> str:
    try:
        return ctx.meta.get("mcp-session-id", "default") or "default"
    except Exception:
        return "default"


def register_abha_verification_tools(mcp: FastMCP, validator: FlowValidator) -> None:

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def verify_abha_init(request: VerifyABHAInitInput, ctx: Context) -> Dict[str, Any]:
        """
        Sends an OTP to the patient via the chosen method to begin ABHA verification.

        Accepts:
        - method: aadhaar_otp | abha_number_aadhaar_otp | abha_number_abha_otp | mobile_otp
        - identifier: must match the chosen method —
            aadhaar_otp              → 12-digit Aadhaar number
            abha_number_* methods    → ABHA number in format 91-XXXX-XXXX-XXXX
            mobile_otp               → 10-digit mobile number
        Returns: txn_id

        The patient will receive an OTP via the chosen method sent by this tool. Ask the patient for that OTP.
        Follow-up: pass the txn_id returned by this tool and the OTP sent by this tool that the patient provides to verify_abha_confirm.

        Do not mismatch method and identifier — the request will be rejected.
        """
        await validator.validate_and_record(_session_id(ctx), "verify_abha_init")
        return await _service.verify_abha_init(request.method, request.identifier)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def verify_abha_confirm(request: VerifyABHAConfirmInput, ctx: Context) -> Dict[str, Any]:
        """
        Verifies the OTP sent by verify_abha_init or selects an ABHA account to complete verification.

        Accepts:
        - txn_id returned by verify_abha_init (first call) or txn_id returned by this tool itself (second call if skip_state = abha_select)
        - otp sent by verify_abha_init that the patient received (first call only)
        - abha_number selected by the patient from abha_profiles (second call only, when skip_state = abha_select)
        Returns: ABHA profile, or skip_state = abha_select with abha_profiles list

        Follow-up:
        - skip_state = abha_select → present abha_profiles to patient, call this tool again with the txn_id returned by this tool and the abha_number the patient selects. Leave otp empty.
        - skip_state = abha_end    → verification complete, profile is in this response

        Do not provide both otp and abha_number in the same call — they serve different sub-steps.
        Do not call without the txn_id from verify_abha_init.
        """
        await validator.validate_and_record(_session_id(ctx), "verify_abha_confirm")
        return await _service.verify_abha_confirm(request.txn_id, request.otp, request.abha_number)
```

- [ ] **Step 3: Update `tools/m1/abha_address_verification_tools.py`**

```python
from typing import Any, Dict
from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.abha_address_verification_service import AbhaAddressVerificationService
from state.validator import FlowValidator
from tools.m1.models import (
    SearchABHAAddressAuthMethodsInput,
    ABHAAddressVerificationInitInput,
    ABHAAddressVerificationConfirmInput,
)

_client = ABDMGatewayClient()
_service = AbhaAddressVerificationService(_client)


def _session_id(ctx: Context) -> str:
    try:
        return ctx.meta.get("mcp-session-id", "default") or "default"
    except Exception:
        return "default"


def register_abha_address_verification_tools(mcp: FastMCP, validator: FlowValidator) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
    async def search_abha_address_auth_methods(request: SearchABHAAddressAuthMethodsInput, ctx: Context) -> Dict[str, Any]:
        """
        Returns the authentication methods available for a given ABHA address.

        Accepts: abha_address (format: name@abdm)
        Returns: list of available auth methods (e.g. mobile, aadhaar)

        Present the available methods to the patient and ask them to choose one.
        Follow-up: pass the same abha_address and the method chosen by the patient to abha_address_verification_init.

        Do not skip this step and hardcode a method — not all methods are available for every ABHA address.
        """
        await validator.validate_and_record(_session_id(ctx), "search_abha_address_auth_methods")
        return await _service.search_abha_address_auth_methods(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def abha_address_verification_init(request: ABHAAddressVerificationInitInput, ctx: Context) -> Dict[str, Any]:
        """
        Sends an OTP to the patient via the chosen auth method to begin ABHA address verification.

        Accepts:
        - abha_address (same address passed to search_abha_address_auth_methods)
        - method returned by search_abha_address_auth_methods and chosen by the patient
        Returns: txn_id

        The patient will receive an OTP via the chosen method sent by this tool. Ask the patient for that OTP.
        Follow-up: pass the txn_id returned by this tool and the OTP sent by this tool that the patient provides to abha_address_verification_confirm.

        Do not use a method not returned by search_abha_address_auth_methods — it will fail.
        Do not call without first calling search_abha_address_auth_methods.
        """
        await validator.validate_and_record(_session_id(ctx), "abha_address_verification_init")
        return await _service.abha_address_verification_init(request.abha_address, request.method)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def abha_address_verification_confirm(request: ABHAAddressVerificationConfirmInput, ctx: Context) -> Dict[str, Any]:
        """
        Verifies the OTP sent by abha_address_verification_init to complete ABHA address verification.

        Accepts:
        - txn_id returned by abha_address_verification_init
        - otp sent by abha_address_verification_init that the patient received and provided
        Returns: verified ABHA profile

        Do not call without the txn_id from abha_address_verification_init.
        Do not call without first completing abha_address_verification_init.
        """
        await validator.validate_and_record(_session_id(ctx), "abha_address_verification_confirm")
        return await _service.abha_address_verification_confirm(request.txn_id, request.otp)
```

- [ ] **Step 4: Update `tools/m1/find_abha_tools.py`** — only the flow tools get validator calls; standalone tools (get_abha_profile, get_abha_qr, get_abha_card, get_session, invalidate_session) do not since they are not in FLOW_RULES

Add `validator: FlowValidator` parameter to `register_find_abha_tools`, add `ctx: Context` to flow tools, add `await validator.validate_and_record(...)` before service calls for: `search_abha`, `find_abha_init`, `find_abha_verify`. Leave the 5 standalone tools unchanged except adding `ctx: Context` is not needed for them.

The four flow tools in find_abha_tools.py become:

```python
from typing import Any, Dict
import base64
from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.find_abha_service import FindAbhaService
from state.validator import FlowValidator
from tools.m1.models import (
    SearchABHAInput,
    FindABHAInitInput,
    FindABHAVerifyInput,
    GetABHAProfileInput,
    GetABHAQRInput,
    GetABHACardInput,
    SessionInput,
)

_client = ABDMGatewayClient()
_service = FindAbhaService(_client)


def _session_id(ctx: Context) -> str:
    try:
        return ctx.meta.get("mcp-session-id", "default") or "default"
    except Exception:
        return "default"


def register_find_abha_tools(mcp: FastMCP, validator: FlowValidator) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
    async def search_abha(request: SearchABHAInput, ctx: Context) -> Dict[str, Any]:
        """
        Searches for ABHA profiles linked to a mobile number.

        Accepts: mobile (10-digit)
        Returns: txn_id, abha (list of matched profiles)

        Present the list to the patient and confirm which profile is theirs.
        Follow-up: pass the txn_id returned by this tool and the index of the profile the patient selected (string position in the abha list, e.g. "0") to find_abha_init.

        Do not assume a single result is correct without patient confirmation — a mobile may be linked to multiple ABHA profiles.
        """
        await validator.validate_and_record(_session_id(ctx), "search_abha")
        return await _service.search_abha(request.mobile)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def find_abha_init(request: FindABHAInitInput, ctx: Context) -> Dict[str, Any]:
        """
        Sends an OTP to verify ownership of the ABHA profile selected from the results returned by search_abha.

        Accepts:
        - txn_id returned by search_abha
        - index (string — position of the profile the patient selected in the abha list returned by search_abha, e.g. "0")
        - otp_system (abdm | aadhaar) — abdm sends OTP to registered mobile, aadhaar sends via UIDAI
        Returns: txn_id

        The patient will receive an OTP via the chosen otp_system sent by this tool. Ask the patient for that OTP.
        Follow-up: pass the txn_id returned by this tool and the OTP sent by this tool that the patient provides to find_abha_verify.

        Do not call without the txn_id from search_abha.
        Do not use an index not from the abha list returned by search_abha.
        """
        await validator.validate_and_record(_session_id(ctx), "find_abha_init")
        return await _service.find_abha_init(request.txn_id, request.index, request.otp_system)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def find_abha_verify(request: FindABHAVerifyInput, ctx: Context) -> Dict[str, Any]:
        """
        Verifies the OTP sent by find_abha_init to retrieve the patient's ABHA profile.

        Accepts:
        - txn_id returned by find_abha_init
        - otp sent by find_abha_init that the patient received and provided
        Returns: ABHA profile

        Do not call without the txn_id from find_abha_init.
        Do not call without first completing find_abha_init.
        """
        await validator.validate_and_record(_session_id(ctx), "find_abha_verify")
        return await _service.find_abha_verify(request.txn_id, request.otp)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_abha_profile(request: GetABHAProfileInput) -> Dict[str, Any]:
        """
        Fetches the current ABHA profile for a patient by their ABHA address.

        Accepts: abha_address (format: name@abdm)
        Returns: name, ABHA number, gender, date of birth, mobile, address, KYC status

        Do not call without an active session for this ABHA address — it will fail. Use get_session to check session state if unsure.
        """
        return await _service.get_abha_profile(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_abha_qr(request: GetABHAQRInput) -> Dict[str, Any]:
        """
        Fetches the ABHA QR code for a patient.

        Accepts: abha_address (format: name@abdm)
        Returns: content_type (image/png), data_base64 (base64-encoded PNG)

        Do not call without an active session for this ABHA address.
        """
        raw_bytes = await _service.get_abha_qr(request.abha_address)
        return {"content_type": "image/png", "data_base64": base64.b64encode(raw_bytes).decode()}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_abha_card(request: GetABHACardInput) -> Dict[str, Any]:
        """
        Fetches the ABHA health card for a patient.

        Accepts: abha_address (format: name@abdm)
        Returns: content_type, data_base64 (base64-encoded PNG or PDF)

        Do not call without an active session for this ABHA address.
        """
        return await _service.get_abha_card(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_session(request: SessionInput) -> Dict[str, Any]:
        """
        Returns the active ABDM session for a patient's ABHA address.

        Accepts: abha_address (format: name@abdm)
        Returns: session details if active, empty if no session exists

        Do not treat a missing session as an error — it means the patient needs to complete a verification flow before profile or assets can be accessed.
        """
        return await _service.get_session(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    async def invalidate_session(request: SessionInput) -> Dict[str, Any]:
        """
        Deletes the active ABDM session for a patient's ABHA address.

        Accepts: abha_address (format: name@abdm)
        Returns: confirmation of deletion

        Do not call unless the intent is to explicitly log out the patient — after this, the patient must complete a verification flow again before profile or assets can be accessed.
        """
        return await _service.invalidate_session(request.abha_address)
```

- [ ] **Step 5: Verify server starts and tools register correctly**

```bash
cd D:\ABDM\abdm-mcp && .venv\Scripts\python.exe server.py --transport stdio
```
Expected: starts, logs "Registering ABHA enrollment tools...", no errors (Ctrl+C to stop)

- [ ] **Step 6: Run all tests**

```bash
cd D:\ABDM\abdm-mcp && .venv\Scripts\python.exe -m pytest tests/ -v
```
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add tools/m1/abha_enrollment_tools.py tools/m1/abha_verification_tools.py tools/m1/abha_address_verification_tools.py tools/m1/find_abha_tools.py
git commit -m "feat: integrate FlowValidator into all tool files"
```

---

### Task 6: Documentation update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add flow enforcement section to README**

Add after the Configuration table:

```markdown
## Flow Enforcement

The MCP server enforces correct tool call sequencing per session. Calling a tool
out of order (e.g. `aadhaar_enrollment_verify_otp` without first calling
`aadhaar_enrollment_init`) returns a descriptive error telling the agent which
tool must be called first.

### Transport requirements

| Transport | Session support | State storage |
|---|---|---|
| stdio | Single session (in-memory) | Python dict |
| Stateful HTTP | `mcp-session-id` per session | Redis |
| Stateless HTTP | None | Not supported |

**Production deployments must use stateful HTTP or stdio.**
Stateless HTTP (`stateless_http=True`) does not carry a session ID and cannot
enforce flow ordering.

### Redis configuration (stateful HTTP only)

Set `ABDM_REDIS_URL` in `.env`:

```env
ABDM_REDIS_URL=redis://localhost:6379
```

If `ABDM_REDIS_URL` is empty, the server falls back to in-memory state
(suitable for single-instance deployments).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add flow enforcement and transport requirements"
```

---

## Self-Review

**Spec coverage:**
- FlowStateStore abstraction ✓ (Task 1)
- InMemoryFlowStateStore for stdio ✓ (Task 1)
- RedisFlowStateStore for stateful HTTP ✓ (Task 2)
- Flow rules per tool ✓ (Task 3)
- Validator logic ✓ (Task 3)
- Transport detection at startup ✓ (Task 4)
- Tool integration ✓ (Task 5)
- Documentation boundary for stateless HTTP ✓ (Task 6)

**Placeholder scan:** No TBDs, no "similar to Task N", all code blocks complete.

**Type consistency:**
- `FlowStateStore.get/set/delete` defined in Task 1, consumed identically in Tasks 2 and 3 ✓
- `FlowValidator.validate_and_record(session_id: str, tool_name: str)` defined in Task 3, called identically in Task 5 ✓
- `register_*(mcp, validator)` signature introduced in Task 4, used identically in Task 5 ✓
- `_session_id(ctx: Context) -> str` helper defined identically in all four tool files ✓
