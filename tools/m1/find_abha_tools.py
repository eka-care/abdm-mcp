import base64
from typing import Any, Dict
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.find_abha_service import FindAbhaService
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


def register_find_abha_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
    async def search_abha(request: SearchABHAInput) -> Dict[str, Any]:
        """
        Search for ABHA profiles linked to a mobile number.
        Returns a list of matching profiles and a txn_id.
        If multiple profiles found, show them to the patient and call find_abha_init with the selected index.
        """
        return await _service.search_abha(request.mobile)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def find_abha_init(request: FindABHAInitInput) -> Dict[str, Any]:
        """
        Send OTP to verify ownership of a specific ABHA profile found via search_abha.
        otp_system: 'abdm' for ABDM mobile OTP, 'aadhaar' for Aadhaar OTP.
        Returns txn_id. Call find_abha_verify next with the OTP.
        """
        return await _service.find_abha_init(request.txn_id, request.index, request.otp_system)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def find_abha_verify(request: FindABHAVerifyInput) -> Dict[str, Any]:
        """
        Verify the OTP to complete the Find ABHA flow and retrieve the patient profile.
        Returns the patient's full ABHA profile and session token on success.
        """
        return await _service.find_abha_verify(request.txn_id, request.otp)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_abha_profile(request: GetABHAProfileInput) -> Dict[str, Any]:
        """
        Fetch the ABHA profile for a patient by their ABHA address.
        Requires an active session for the given ABHA address.
        Returns name, ABHA number, gender, date of birth, mobile, address, and KYC status.
        """
        return await _service.get_abha_profile(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_abha_qr(request: GetABHAQRInput) -> Dict[str, Any]:
        """
        Fetch the ABHA QR code image for a patient as a base64-encoded PNG.
        Returns base64-encoded PNG data and content_type.
        """
        raw_bytes = await _service.get_abha_qr(request.abha_address)
        return {"content_type": "image/png", "data_base64": base64.b64encode(raw_bytes).decode()}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_abha_card(request: GetABHACardInput) -> Dict[str, Any]:
        """
        Fetch the ABHA health card for a patient as a base64-encoded file.
        Returns base64-encoded card data and content_type (PNG or PDF).
        """
        return await _service.get_abha_card(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_session(request: SessionInput) -> Dict[str, Any]:
        """
        Get the active ABDM session for an ABHA address.
        Returns session details if an active session exists.
        """
        return await _service.get_session(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    async def invalidate_session(request: SessionInput) -> Dict[str, Any]:
        """
        Invalidate and delete the active ABDM session for an ABHA address.
        After invalidation, the patient must re-verify to create a new session.
        """
        return await _service.invalidate_session(request.abha_address)
