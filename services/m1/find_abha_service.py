from typing import Any, Dict
from clients.abdm_gateway_client import ABDMGatewayClient


class FindAbhaService:
    def __init__(self, client: ABDMGatewayClient):
        self._client = client

    async def search_abha(self, mobile: str) -> Dict[str, Any]:
        return await self._client.search_abha(mobile)

    async def find_abha_init(self, txn_id: str, index: str, otp_system: str) -> Dict[str, Any]:
        return await self._client.find_abha_init(txn_id, index, otp_system)

    async def find_abha_verify(self, txn_id: str, otp: str) -> Dict[str, Any]:
        return await self._client.find_abha_verify(txn_id, otp)

    async def get_abha_profile(self, abha_address: str) -> Dict[str, Any]:
        return await self._client.get_abha_profile(abha_address)

    async def get_abha_qr(self, abha_address: str) -> bytes:
        return await self._client.get_abha_qr(abha_address)

    async def get_abha_card(self, abha_address: str) -> Dict[str, Any]:
        return await self._client.get_abha_card(abha_address)

    async def get_session(self, abha_address: str) -> Dict[str, Any]:
        return await self._client.get_session(abha_address)

    async def invalidate_session(self, abha_address: str) -> Dict[str, Any]:
        return await self._client.invalidate_session(abha_address)
