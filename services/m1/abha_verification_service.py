from typing import Any, Dict, Optional
from clients.abdm_gateway_client import ABDMGatewayClient


class AbhaVerificationService:
    def __init__(self, client: ABDMGatewayClient):
        self._client = client

    async def verify_abha_init(self, method: str, identifier: str) -> Dict[str, Any]:
        return await self._client.verify_abha_init(method, identifier)

    async def verify_abha_confirm(self, txn_id: str, otp: Optional[str], abha_number: Optional[str]) -> Dict[str, Any]:
        return await self._client.verify_abha_confirm(txn_id, otp, abha_number)
