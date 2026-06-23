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
        STEP 1 of the Find ABHA flow. Call this to look up ABHA profiles by mobile number.

        Ask the patient for the 10-digit mobile number linked to their ABHA.

        Response contains a txn_id and an abha_profiles list.
        If one profile is returned, confirm with the patient and proceed.
        If multiple profiles are returned, show them to the patient and ask which one is theirs.

        Call find_abha_init next with the txn_id from this response and the index
        of the profile the patient selected (index starts from the list position, check response format).
        """
        return await _service.search_abha(request.mobile)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def find_abha_init(request: FindABHAInitInput) -> Dict[str, Any]:
        """
        STEP 2 of the Find ABHA flow. Call this after search_abha.

        Use the txn_id from search_abha's response.
        Use the index of the profile the patient selected from the abha_profiles list.

        Choose otp_system based on what the patient prefers:
        - 'abdm'    → OTP sent to the patient's registered mobile via ABDM
        - 'aadhaar' → OTP sent via UIDAI (requires Aadhaar-linked mobile)

        Response contains txn_id. Save it for the next step.
        Call find_abha_verify next with the txn_id from this response and the OTP the patient receives.
        """
        return await _service.find_abha_init(request.txn_id, request.index, request.otp_system)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def find_abha_verify(request: FindABHAVerifyInput) -> Dict[str, Any]:
        """
        FINAL STEP of the Find ABHA flow. Call this after find_abha_init.

        Use the txn_id from find_abha_init's response.
        Ask the patient for the OTP they received.

        On success, response contains the patient's full ABHA profile.
        No further tool call needed.
        """
        return await _service.find_abha_verify(request.txn_id, request.otp)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_abha_profile(request: GetABHAProfileInput) -> Dict[str, Any]:
        """
        Fetch the current ABHA profile for a patient using their ABHA address (e.g. name@abdm).

        Use this after any enrollment or verification flow has completed and you need
        to retrieve or display the patient's latest profile details.

        Returns name, ABHA number, gender, date of birth, mobile, address, and KYC status.
        """
        return await _service.get_abha_profile(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_abha_qr(request: GetABHAQRInput) -> Dict[str, Any]:
        """
        Fetch the ABHA QR code for a patient using their ABHA address (e.g. name@abdm).

        Use this when the patient needs their QR code to share with another
        ABDM-connected facility for scan & share.

        Response contains base64-encoded PNG data and content_type ('image/png').
        Decode and display or print the QR for the patient.
        """
        raw_bytes = await _service.get_abha_qr(request.abha_address)
        return {"content_type": "image/png", "data_base64": base64.b64encode(raw_bytes).decode()}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_abha_card(request: GetABHACardInput) -> Dict[str, Any]:
        """
        Fetch the ABHA health card for a patient using their ABHA address (e.g. name@abdm).

        The health card contains the patient's ABHA number, name, photo, and QR code.
        Use this when the patient needs a printable or downloadable copy of their ABHA card.

        Response contains base64-encoded card data and content_type (PNG or PDF).
        """
        return await _service.get_abha_card(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_session(request: SessionInput) -> Dict[str, Any]:
        """
        Check whether an active ABDM session exists for a patient's ABHA address.

        Sessions are created automatically during enrollment and verification flows.
        Use this to check session status before attempting profile or asset fetches.

        Returns session details if active. If no session exists, the patient must
        go through a verification flow first.
        """
        return await _service.get_session(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    async def invalidate_session(request: SessionInput) -> Dict[str, Any]:
        """
        Delete the active ABDM session for a patient's ABHA address.

        Use this to log the patient out or clear a stale session.
        After calling this, the patient's session is gone — they must complete
        a verification flow again before their profile or assets can be accessed.
        """
        return await _service.invalidate_session(request.abha_address)
