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

_client = ABDMGatewayClient()
_service = AbhaEnrollmentService(_client)


def _session_id(ctx: Context) -> str:
    try:
        return ctx.session_id or "default"
    except RuntimeError:
        return "default"


def register_abha_enrollment_tools(mcp: FastMCP, validator: FlowValidator) -> None:

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
        return await _service.aadhaar_enrollment_init(request.aadhaar_number)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_verify_otp(request: AadhaarEnrollmentVerifyOTPInput, ctx: Context) -> Dict[str, Any]:
        """
        Verifies the OTP sent by aadhaar_enrollment_init and the patient's mobile number, and advances the enrollment state.

        Accepts:
        - txn_id returned by aadhaar_enrollment_init
        - otp sent by aadhaar_enrollment_init that the patient received on their Aadhaar-linked mobile
        - mobile (10-digit mobile number provided by the patient)
        Returns: txn_id, skip_state, and optionally a list of existing ABHA profiles linked to this Aadhaar

        There are three cases based on what ABDM finds:

        Case 1 — No existing ABHA:
        skip_state = abha_create → pass the txn_id returned by this tool to aadhaar_enrollment_suggest_address to continue creating a new ABHA.

        Case 2 — Existing ABHA found, mobile matches the registered mobile of an existing profile:
        skip_state = abha_end, response includes existing ABHA profiles.
        Present the profiles to the patient and ask: do you want to log into one of these existing profiles, or create a new ABHA address?
        - Login into existing → patient selects a profile, then start a fresh verification flow based on their preference: verify_abha_init → verify_abha_confirm (by ABHA number) or search_abha_address_auth_methods → abha_address_verification_init → abha_address_verification_confirm (by ABHA address). Do not continue this enrollment flow.
        - Create new → pass the txn_id returned by this tool to aadhaar_enrollment_suggest_address.

        Case 3 — Existing ABHA found, mobile does not match the registered mobile of an existing profile:
        skip_state = confirm_mobile_otp → a new OTP has been sent to the patient's provided mobile for secondary verification. Ask the patient for that OTP and pass the txn_id returned by this tool and that OTP to aadhaar_enrollment_verify_mobile_otp. After that step, the same choice as Case 2 will apply.

        Do not call without the txn_id from aadhaar_enrollment_init.
        """
        await validator.validate_and_record(_session_id(ctx), "aadhaar_enrollment_verify_otp")
        return await _service.aadhaar_enrollment_verify_otp(request.txn_id, request.otp, request.mobile)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_verify_mobile_otp(request: AadhaarEnrollmentVerifyMobileOTPInput, ctx: Context) -> Dict[str, Any]:
        """
        Verifies the secondary OTP sent to the patient's mobile when aadhaar_enrollment_verify_otp returned skip_state = confirm_mobile_otp (i.e. the provided mobile did not match the registered mobile of an existing ABHA).

        Accepts:
        - txn_id returned by aadhaar_enrollment_verify_otp
        - otp sent to the patient's mobile by aadhaar_enrollment_verify_otp
        Returns: txn_id, skip_state, and optionally a list of existing ABHA profiles

        After this step the same two outcomes apply as Case 2 in aadhaar_enrollment_verify_otp:
        - skip_state = abha_end, response includes existing ABHA profiles → present the profiles to the patient and ask: log into an existing profile or create a new ABHA address?
          - Login into existing → patient selects a profile, start a fresh verification flow: verify_abha_init → verify_abha_confirm (by ABHA number) or search_abha_address_auth_methods → abha_address_verification_init → abha_address_verification_confirm (by ABHA address). Do not continue this enrollment flow.
          - Create new → pass the txn_id returned by this tool to aadhaar_enrollment_suggest_address.
        - skip_state = abha_create → no existing ABHA found, pass the txn_id returned by this tool to aadhaar_enrollment_suggest_address.

        Do not call unless aadhaar_enrollment_verify_otp returned skip_state = confirm_mobile_otp.
        Do not use the txn_id from aadhaar_enrollment_init — use the txn_id from aadhaar_enrollment_verify_otp.
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
