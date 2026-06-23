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
        STEP 1 of ABHA verification. Call this first to verify a patient's existing ABHA.

        Choose a method based on what identifier the patient provides:
        - 'aadhaar_otp'              → patient provides Aadhaar number, OTP sent via UIDAI
        - 'abha_number_aadhaar_otp'  → patient provides ABHA number (14-digit), OTP sent via UIDAI
        - 'abha_number_abha_otp'     → patient provides ABHA number (14-digit), OTP sent via ABDM
        - 'mobile_otp'               → patient provides mobile number, OTP sent via ABDM

        The identifier must match the chosen method:
        - aadhaar_otp              → 12-digit Aadhaar number
        - abha_number_* methods    → ABHA number in format 91-XXXX-XXXX-XXXX
        - mobile_otp               → 10-digit mobile number

        Response contains txn_id. Save it for the next step.
        Call verify_abha_confirm next with the txn_id from this response and the OTP the patient receives.
        """
        return await _service.verify_abha_init(request.method, request.identifier)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def verify_abha_confirm(request: VerifyABHAConfirmInput) -> Dict[str, Any]:
        """
        STEP 2 of ABHA verification. Call this after verify_abha_init.

        Use the txn_id from verify_abha_init's response.

        This tool handles two sub-steps depending on what the response returns:

        Sub-step A — OTP verification (always the first call):
          Provide txn_id + otp (the OTP the patient received). Leave abha_number empty.

        Sub-step B — Account selection (only if response contains skip_state = 'abha_select'):
          The response will contain an abha_profiles list. Show it to the patient, let them pick.
          Call this tool again with txn_id + abha_number (the ABHA number they selected). Leave otp empty.

        Final response (skip_state = 'abha_end') contains the patient's verified ABHA profile.
        Stop here — no further tool call needed.
        """
        return await _service.verify_abha_confirm(request.txn_id, request.otp, request.abha_number)
