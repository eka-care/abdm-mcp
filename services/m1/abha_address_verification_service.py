from typing import Any, Dict
from clients.abdm_gateway_client import ABDMGatewayClient


class AbhaAddressVerificationService:
    def __init__(self, client: ABDMGatewayClient):
        self._client = client

    async def search_abha_address_auth_methods(self, abha_address: str) -> Dict[str, Any]:
        return await self._client.search_abha_address_auth_methods(abha_address)

    async def abha_address_verification_init(self, abha_address: str, method: str) -> Dict[str, Any]:
        return await self._client.abha_address_verification_init(abha_address, method)

    async def abha_address_verification_confirm(self, txn_id: str, otp: str) -> Dict[str, Any]:
        return await self._client.abha_address_verification_confirm(txn_id, otp)
