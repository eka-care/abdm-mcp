from typing import Any, Dict
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.abha_address_verification_service import AbhaAddressVerificationService
from tools.m1.models import (
    SearchABHAAddressAuthMethodsInput,
    ABHAAddressVerificationInitInput,
    ABHAAddressVerificationConfirmInput,
)

_client = ABDMGatewayClient()
_service = AbhaAddressVerificationService(_client)


def register_abha_address_verification_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
    async def search_abha_address_auth_methods(request: SearchABHAAddressAuthMethodsInput) -> Dict[str, Any]:
        """
        Look up available authentication methods for an ABHA address (e.g. patient@abdm).
        Call this first to find out whether 'mobile' or 'aadhaar' verification is available.
        """
        return await _service.search_abha_address_auth_methods(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def abha_address_verification_init(request: ABHAAddressVerificationInitInput) -> Dict[str, Any]:
        """
        Start ABHA address verification. Sends an OTP to the patient via the chosen method.
        Call search_abha_address_auth_methods first to get available methods.
        Returns txn_id. Call abha_address_verification_confirm next with the OTP.
        """
        return await _service.abha_address_verification_init(request.abha_address, request.method)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def abha_address_verification_confirm(request: ABHAAddressVerificationConfirmInput) -> Dict[str, Any]:
        """
        Confirm ABHA address verification with OTP. Final step of the address verification flow.
        Returns the patient's ABHA profile on success.
        """
        return await _service.abha_address_verification_confirm(request.txn_id, request.otp)
