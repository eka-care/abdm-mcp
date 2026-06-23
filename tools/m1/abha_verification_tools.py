from typing import Any, Dict
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.abha_verification_service import AbhaVerificationService
from tools.m1.models import VerifyABHAInitInput, VerifyABHAConfirmInput

_client = ABDMGatewayClient()
_service = AbhaVerificationService(_client)


def register_abha_verification_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def verify_abha_init(request: VerifyABHAInitInput) -> Dict[str, Any]:
        """
        Initiate ABHA verification. Sends an OTP to the patient based on the chosen method.

        Methods:
        - 'aadhaar_otp': Aadhaar number, OTP via UIDAI
        - 'abha_number_aadhaar_otp': ABHA number, OTP via UIDAI
        - 'abha_number_abha_otp': ABHA number, OTP via ABDM
        - 'mobile_otp': mobile number, OTP via ABDM (may return multiple accounts)

        Returns txn_id. Call verify_abha_confirm next with the OTP.
        """
        return await _service.verify_abha_init(request.method, request.identifier)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def verify_abha_confirm(request: VerifyABHAConfirmInput) -> Dict[str, Any]:
        """
        Confirm ABHA verification with OTP, or select an account when multiple are returned.

        OTP step: provide txn_id + otp (leave abha_number empty).
        Account selection (skip_state='abha_select'): provide txn_id + abha_number (leave otp empty).

        Returns profile on success (skip_state='abha_end') or abha_profiles list for selection.
        """
        return await _service.verify_abha_confirm(request.txn_id, request.otp, request.abha_number)
