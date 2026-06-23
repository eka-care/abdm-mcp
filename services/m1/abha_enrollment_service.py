from typing import Any, Dict
from clients.abdm_gateway_client import ABDMGatewayClient


class AbhaEnrollmentService:
    def __init__(self, client: ABDMGatewayClient):
        self._client = client

    async def aadhaar_enrollment_init(self, aadhaar_number: str) -> Dict[str, Any]:
        return await self._client.aadhaar_enrollment_init(aadhaar_number)

    async def aadhaar_enrollment_verify_otp(self, txn_id: str, otp: str, mobile: str) -> Dict[str, Any]:
        return await self._client.aadhaar_enrollment_verify_otp(txn_id, otp, mobile)

    async def aadhaar_enrollment_verify_mobile_otp(self, txn_id: str, otp: str) -> Dict[str, Any]:
        return await self._client.aadhaar_enrollment_verify_mobile_otp(txn_id, otp)

    async def aadhaar_enrollment_suggest_address(self, txn_id: str, user_detail: Dict[str, Any]) -> Dict[str, Any]:
        return await self._client.aadhaar_enrollment_suggest_address(txn_id, user_detail)

    async def aadhaar_enrollment_create_address(self, txn_id: str, abha_address: str) -> Dict[str, Any]:
        return await self._client.aadhaar_enrollment_create_address(txn_id, abha_address)

    async def enroll_abha_by_biometric(self, aadhaar_number: str, pid: str, mobile_number: str) -> Dict[str, Any]:
        return await self._client.enroll_abha_by_biometric(aadhaar_number, pid, mobile_number)
