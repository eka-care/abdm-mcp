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
        Verifies the OTP sent by aadhaar_enrollment_init and advances the enrollment state.

        Accepts:
        - txn_id returned by aadhaar_enrollment_init
        - otp sent by aadhaar_enrollment_init that the patient received on their Aadhaar-linked mobile
        - mobile (10-digit, provided by the patient)
        Returns: txn_id, skip_state, and optionally a list of existing ABHA profiles linked to this Aadhaar

        Follow-up depends on skip_state:
        - confirm_mobile_otp → a new OTP has been sent to the patient's mobile, ask the patient for that OTP, pass the txn_id returned by this tool and that OTP to aadhaar_enrollment_verify_mobile_otp
        - abha_create        → no existing ABHA found, or patient wants a new address — pass the txn_id returned by this tool to aadhaar_enrollment_suggest_address
        - abha_end           → enrollment complete, ABHA profile is in this response

        If the response includes existing ABHA profiles, present them to the patient and ask: do you want to log into one of these existing profiles, or create a new ABHA address? Wait for the patient's answer before proceeding.
        - Patient wants to log in → ask whether they prefer to verify by ABHA number (verify_abha_init → verify_abha_confirm) or by ABHA address (search_abha_address_auth_methods → abha_address_verification_init → abha_address_verification_confirm), then use the chosen flow (do not continue this enrollment flow)
        - Patient wants a new address → continue with aadhaar_enrollment_suggest_address using the txn_id returned by this tool

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
