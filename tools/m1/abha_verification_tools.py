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
        return ctx.session_id or "default"
    except RuntimeError:
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
        - skip_state = abha_select → present abha_profiles to patient exactly as returned, call this tool again with the txn_id returned by this tool and the abha_number the patient selects. Leave otp empty.
        - skip_state = abha_end    → verification complete, profile is in this response — present every field to the patient, formatted clearly but with nothing omitted.

        Do not provide both otp and abha_number in the same call — they serve different sub-steps.
        Do not call without the txn_id from verify_abha_init.
        """
        await validator.validate_and_record(_session_id(ctx), "verify_abha_confirm")
        return await _service.verify_abha_confirm(request.txn_id, request.otp, request.abha_number)
