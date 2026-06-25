import base64
from typing import Any, Dict
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
