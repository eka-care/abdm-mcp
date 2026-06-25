from typing import Any, Dict
from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.abha_address_verification_service import AbhaAddressVerificationService
from state.validator import FlowValidator
from tools.m1.models import (
    SearchABHAAddressAuthMethodsInput,
    ABHAAddressVerificationInitInput,
    ABHAAddressVerificationConfirmInput,
)

_client = ABDMGatewayClient()
_service = AbhaAddressVerificationService(_client)


def _session_id(ctx: Context) -> str:
    try:
        return ctx.session_id or "default"
    except RuntimeError:
        return "default"


def register_abha_address_verification_tools(mcp: FastMCP, validator: FlowValidator) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
    async def search_abha_address_auth_methods(request: SearchABHAAddressAuthMethodsInput, ctx: Context) -> Dict[str, Any]:
        """
        Returns the authentication methods available for a given ABHA address.

        Accepts: abha_address (format: name@abdm)
        Returns: list of available auth methods (e.g. mobile, aadhaar)

        Present the available methods to the patient and ask them to choose one.
        Follow-up: pass the same abha_address and the method chosen by the patient to abha_address_verification_init.

        Do not skip this step and hardcode a method — not all methods are available for every ABHA address.
        """
        await validator.validate_and_record(_session_id(ctx), "search_abha_address_auth_methods")
        return await _service.search_abha_address_auth_methods(request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def abha_address_verification_init(request: ABHAAddressVerificationInitInput, ctx: Context) -> Dict[str, Any]:
        """
        Sends an OTP to the patient via the chosen auth method to begin ABHA address verification.

        Accepts:
        - abha_address (same address passed to search_abha_address_auth_methods)
        - method returned by search_abha_address_auth_methods and chosen by the patient
        Returns: txn_id

        The patient will receive an OTP via the chosen method sent by this tool. Ask the patient for that OTP.
        Follow-up: pass the txn_id returned by this tool and the OTP sent by this tool that the patient provides to abha_address_verification_confirm.

        Do not use a method not returned by search_abha_address_auth_methods — it will fail.
        Do not call without first calling search_abha_address_auth_methods.
        """
        await validator.validate_and_record(_session_id(ctx), "abha_address_verification_init")
        return await _service.abha_address_verification_init(request.abha_address, request.method)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def abha_address_verification_confirm(request: ABHAAddressVerificationConfirmInput, ctx: Context) -> Dict[str, Any]:
        """
        Verifies the OTP sent by abha_address_verification_init to complete ABHA address verification.

        Accepts:
        - txn_id returned by abha_address_verification_init
        - otp sent by abha_address_verification_init that the patient received and provided
        Returns: verified ABHA profile

        Do not call without the txn_id from abha_address_verification_init.
        Do not call without first completing abha_address_verification_init.
        """
        await validator.validate_and_record(_session_id(ctx), "abha_address_verification_confirm")
        return await _service.abha_address_verification_confirm(request.txn_id, request.otp)
