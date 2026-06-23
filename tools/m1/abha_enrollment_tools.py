from typing import Any, Dict
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.abha_enrollment_service import AbhaEnrollmentService
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


def register_abha_enrollment_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_init(request: AadhaarEnrollmentInitInput) -> Dict[str, Any]:
        """
        STEP 1 of Aadhaar enrollment. Call this first to begin enrolling a patient for ABHA.

        Sends an OTP to the mobile number linked to the patient's Aadhaar.
        Ask the patient for their 12-digit Aadhaar number before calling this.

        Response contains txn_id. Save it — every subsequent step in this enrollment
        session requires it.

        Call aadhaar_enrollment_verify_otp next with the txn_id from this response
        and the OTP the patient receives on their mobile.
        """
        return await _service.aadhaar_enrollment_init(request.aadhaar_number)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_verify_otp(request: AadhaarEnrollmentVerifyOTPInput) -> Dict[str, Any]:
        """
        STEP 2 of Aadhaar enrollment. Call this after aadhaar_enrollment_init.

        Use the txn_id from aadhaar_enrollment_init's response.
        Ask the patient for the OTP they received and their 10-digit mobile number.

        Response contains txn_id and skip_state. Based on skip_state, call next:
        - 'confirm_mobile_otp' → call aadhaar_enrollment_verify_mobile_otp(txn_id from this response, new OTP patient receives)
        - 'abha_create'        → call aadhaar_enrollment_suggest_address(txn_id from this response)
        - 'abha_select'        → show abha_profiles list from this response to the patient, let them pick one, no further tool call needed unless creating new address
        - 'abha_end'           → enrollment complete, patient's ABHA profile is in this response, stop here
        """
        return await _service.aadhaar_enrollment_verify_otp(request.txn_id, request.otp, request.mobile)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_verify_mobile_otp(request: AadhaarEnrollmentVerifyMobileOTPInput) -> Dict[str, Any]:
        """
        STEP 3a of Aadhaar enrollment. Call this only when aadhaar_enrollment_verify_otp
        returned skip_state = 'confirm_mobile_otp'.

        Use the txn_id from aadhaar_enrollment_verify_otp's response.
        Ask the patient for the new OTP they received on their mobile.

        Response contains txn_id and updated skip_state. Based on skip_state, call next:
        - 'abha_create' → call aadhaar_enrollment_suggest_address(txn_id from this response)
        - 'abha_select' → show abha_profiles list to the patient
        - 'abha_end'    → enrollment complete, ABHA profile is in this response, stop here
        """
        return await _service.aadhaar_enrollment_verify_mobile_otp(request.txn_id, request.otp)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def aadhaar_enrollment_suggest_address(request: AadhaarEnrollmentSuggestAddressInput) -> Dict[str, Any]:
        """
        STEP 3b of Aadhaar enrollment. Call this only when a previous step returned
        skip_state = 'abha_create'.

        Use the txn_id from that step's response.
        Optionally provide the patient's name and date of birth in user_detail to get
        more personalized suggestions — leave fields empty if not available.

        Response contains a list of suggested ABHA addresses.
        Show the list to the patient and ask them to pick one.

        Call aadhaar_enrollment_create_address next with the txn_id from this response
        and the abha_address the patient chose.
        """
        return await _service.aadhaar_enrollment_suggest_address(request.txn_id, request.user_detail.model_dump())

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_create_address(request: AadhaarEnrollmentCreateAddressInput) -> Dict[str, Any]:
        """
        FINAL STEP of Aadhaar enrollment. Call this after aadhaar_enrollment_suggest_address.

        Use the txn_id from aadhaar_enrollment_suggest_address's response.
        Use the abha_address the patient selected from the suggestions list (without @abdm suffix).

        On success, response contains the patient's complete ABHA profile.
        Enrollment is now done — no further tool call needed.
        """
        return await _service.aadhaar_enrollment_create_address(request.txn_id, request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def enroll_abha_by_biometric(request: EnrollABHAByBiometricInput) -> Dict[str, Any]:
        """
        Single-step ABHA enrollment using biometric authentication (fingerprint or iris via UIDAI).
        Use this instead of the Aadhaar OTP flow when a biometric device is available.

        Requires the patient's Aadhaar number, mobile number, and the PID block
        captured from the biometric device.

        On success, response contains the patient's complete ABHA profile.
        No follow-up tool call needed.
        """
        return await _service.enroll_abha_by_biometric(request.aadhaar_number, request.pid, request.mobile_number)
