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
        Start ABHA enrollment using Aadhaar. Sends an OTP to the Aadhaar-linked mobile number.
        Step 1 of the Aadhaar enrollment flow. Returns txn_id for the next step.
        Call aadhaar_enrollment_verify_otp next.
        """
        return await _service.aadhaar_enrollment_init(request.aadhaar_number)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_verify_otp(request: AadhaarEnrollmentVerifyOTPInput) -> Dict[str, Any]:
        """
        Verify the Aadhaar OTP to continue enrollment. Step 2 of the Aadhaar enrollment flow.

        Returns txn_id and skip_state:
        - 'confirm_mobile_otp' → call aadhaar_enrollment_verify_mobile_otp
        - 'abha_end' → enrollment complete, profile returned
        - 'abha_select' → multiple existing ABHA accounts, show to user
        - 'abha_create' → call aadhaar_enrollment_suggest_address
        """
        return await _service.aadhaar_enrollment_verify_otp(request.txn_id, request.otp, request.mobile)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_verify_mobile_otp(request: AadhaarEnrollmentVerifyMobileOTPInput) -> Dict[str, Any]:
        """
        Verify mobile OTP during Aadhaar enrollment. Called when skip_state is 'confirm_mobile_otp'.
        Returns txn_id and updated skip_state.
        """
        return await _service.aadhaar_enrollment_verify_mobile_otp(request.txn_id, request.otp)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def aadhaar_enrollment_suggest_address(request: AadhaarEnrollmentSuggestAddressInput) -> Dict[str, Any]:
        """
        Get ABHA address suggestions for the patient. Called when skip_state is 'abha_create'.
        Returns a list of suggested ABHA addresses.
        Pass the chosen address to aadhaar_enrollment_create_address.
        """
        return await _service.aadhaar_enrollment_suggest_address(request.txn_id, request.user_detail.model_dump())

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_create_address(request: AadhaarEnrollmentCreateAddressInput) -> Dict[str, Any]:
        """
        Create the ABHA address — final step of Aadhaar enrollment.
        Pass the abha_address chosen from aadhaar_enrollment_suggest_address results.
        Returns the complete ABHA profile with token on success.
        """
        return await _service.aadhaar_enrollment_create_address(request.txn_id, request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def enroll_abha_by_biometric(request: EnrollABHAByBiometricInput) -> Dict[str, Any]:
        """
        Enroll a patient for ABHA using biometric authentication (fingerprint/iris via UIDAI).
        Use instead of the OTP flow when a biometric device is available.
        Returns the complete ABHA profile on success.
        """
        return await _service.enroll_abha_by_biometric(request.aadhaar_number, request.pid, request.mobile_number)
