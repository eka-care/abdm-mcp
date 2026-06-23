from typing import Any, Dict, Optional
import httpx

from config.settings import settings


class ABDMGatewayClient:
    def __init__(self):
        self._base_url = settings.gateway_base_url
        self._timeout = settings.gateway_timeout
        self._facility_id = settings.facility_id
        self._gateway_api_key = settings.gateway_api_key

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._gateway_api_key}",
            "X-Facility-ID": self._facility_id,
        }
        if extra_headers:
            headers.update(extra_headers)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(
                method=method,
                url=f"{self._base_url}{path}",
                headers=headers,
                json=json,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    # ── Aadhaar Enrollment ──────────────────────────────────────────────────

    async def aadhaar_enrollment_init(self, aadhaar_number: str) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/registration/aadhaar/init",
                                   json={"aadhaar_number": aadhaar_number})

    async def aadhaar_enrollment_verify_otp(
        self, txn_id: str, otp: str, mobile: str
    ) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/registration/aadhaar/verify",
                                   json={"txn_id": txn_id, "otp": otp, "mobile": mobile})

    async def aadhaar_enrollment_verify_mobile_otp(
        self, txn_id: str, otp: str
    ) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/registration/aadhaar/mobile/verify",
                                   json={"txn_id": txn_id, "otp": otp})

    async def aadhaar_enrollment_suggest_address(
        self, txn_id: str, user_detail: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/registration/aadhaar/suggest",
                                   json={"txn_id": txn_id, "flow": "aadhaar",
                                         "user_detail": user_detail})

    async def aadhaar_enrollment_create_address(
        self, txn_id: str, abha_address: str
    ) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/registration/aadhaar/create",
                                   json={"txn_id": txn_id, "abha_address": abha_address})

    async def enroll_abha_by_biometric(
        self, aadhaar_number: str, pid: str, mobile_number: str
    ) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/registration/aadhaar/enroll/bio",
                                   json={"aadhaar_number": aadhaar_number,
                                         "pid": pid, "mobile_number": mobile_number})

    # ── ABHA Verification ───────────────────────────────────────────────────

    async def verify_abha_init(self, method: str, identifier: str) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/verify/init",
                                   json={"method": method, "identifier": identifier})

    async def verify_abha_confirm(
        self, txn_id: str, otp: Optional[str] = None, abha_number: Optional[str] = None
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"txn_id": txn_id}
        if otp:
            body["otp"] = otp
        if abha_number:
            body["abha_number"] = abha_number
        return await self._request("POST", "/api/v1/verify/confirm", json=body)

    # ── ABHA Address Verification ───────────────────────────────────────────

    async def search_abha_address_auth_methods(self, abha_address: str) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/verify/address/search",
                                   json={"abha_address": abha_address})

    async def abha_address_verification_init(
        self, abha_address: str, method: str
    ) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/verify/address/init",
                                   json={"abha_address": abha_address, "method": method})

    async def abha_address_verification_confirm(
        self, txn_id: str, otp: str
    ) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/verify/address/confirm",
                                   json={"txn_id": txn_id, "otp": otp})

    # ── Find ABHA ───────────────────────────────────────────────────────────

    async def search_abha(self, mobile: str) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/profile/search",
                                   json={"mobile": mobile})

    async def find_abha_init(
        self, txn_id: str, index: str, otp_system: str
    ) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/profile/search/init",
                                   json={"txn_id": txn_id, "index": index,
                                         "otp_system": otp_system})

    async def find_abha_verify(self, txn_id: str, otp: str) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/profile/search/verify",
                                   json={"txn_id": txn_id, "otp": otp})

    # ── Profile & Assets ────────────────────────────────────────────────────

    async def get_abha_profile(self, abha_address: str) -> Dict[str, Any]:
        return await self._request("GET", "/api/v1/profile/",
                                   extra_headers={"X-Abha-Address": abha_address})

    async def get_abha_qr(self, abha_address: str) -> bytes:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._gateway_api_key}",
            "X-Facility-ID": self._facility_id,
            "X-Abha-Address": abha_address,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/api/v1/profile/qr", headers=headers
            )
            response.raise_for_status()
            return response.content

    async def get_abha_card(self, abha_address: str) -> Dict[str, Any]:
        import base64
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._gateway_api_key}",
            "X-Facility-ID": self._facility_id,
            "X-Abha-Address": abha_address,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/api/v1/profile/card", headers=headers
            )
            response.raise_for_status()
            return {
                "content_type": response.headers.get("content-type", ""),
                "data_base64": base64.b64encode(response.content).decode()
            }

    # ── Session ─────────────────────────────────────────────────────────────

    async def get_session(self, abha_address: str) -> Dict[str, Any]:
        return await self._request("GET", f"/api/v1/session/{abha_address}")

    async def invalidate_session(self, abha_address: str) -> Dict[str, Any]:
        return await self._request("DELETE", f"/api/v1/session/{abha_address}")
