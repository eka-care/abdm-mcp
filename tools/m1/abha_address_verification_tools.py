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
        STEP 1 of ABHA address verification. Call this first to discover available auth methods.

        Ask the patient for their ABHA address (format: name@abdm) before calling this.

        Response contains a list of available auth methods for that address (e.g. 'mobile', 'aadhaar').
        Show the options to the patient and let them choose.

        Call abha_address_verification_init next with the same abha_address and the chosen method.
        """
        return await _service.search_abha_address_auth_methods(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def abha_address_verification_init(request: ABHAAddressVerificationInitInput) -> Dict[str, Any]:
        """
        STEP 2 of ABHA address verification. Call this after search_abha_address_auth_methods.

        Use the same abha_address from step 1 and the method the patient chose
        from the available methods returned in that response.

        Sends an OTP to the patient via the chosen method.

        Response contains txn_id. Save it for the next step.
        Call abha_address_verification_confirm next with the txn_id from this response
        and the OTP the patient receives.
        """
        return await _service.abha_address_verification_init(request.abha_address, request.method)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def abha_address_verification_confirm(request: ABHAAddressVerificationConfirmInput) -> Dict[str, Any]:
        """
        FINAL STEP of ABHA address verification. Call this after abha_address_verification_init.

        Use the txn_id from abha_address_verification_init's response.
        Ask the patient for the OTP they received.

        On success, response contains the patient's verified ABHA profile.
        No further tool call needed.
        """
        return await _service.abha_address_verification_confirm(request.txn_id, request.otp)
