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
