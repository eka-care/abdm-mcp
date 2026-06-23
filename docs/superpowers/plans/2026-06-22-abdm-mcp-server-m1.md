# ABDM MCP Server — M1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastMCP server that wraps the ABDM Compliance Gateway's M1 endpoints (ABHA enrollment, verification, ABHA address verification, find ABHA, profile/assets, session) as MCP tools callable by AI agents.

**Architecture:** A Python FastMCP server sits in front of the Go ABDM gateway. Credentials (`facility_id`, `gateway_api_key`) are static config in `.env` — the MCP instance itself is the facility identity. No auth layer. Tool discovery and access control are the MCP client's responsibility, not the server's. Supports both `http` and `stdio` transports.

**Deployment model:** One MCP instance per facility. `facility_id` and `gateway_api_key` are baked into the instance's config. Anyone who wants multi-tenant auth can add FastMCP middleware on top — the server is intentionally minimal.

**Tech Stack:** Python 3.11+, fastmcp>=2.0.0, httpx>=0.24.0, pydantic>=2.0.0, pydantic-settings>=2.0.0, python-dotenv>=1.0.0

---

## File Map

```
abdm-mcp/
├── server.py                                        ← FastMCP instance, registers all tools, runs
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── config/
│   ├── __init__.py
│   └── settings.py                                  ← gateway_base_url, gateway_timeout, facility_id, gateway_api_key
│
├── clients/
│   ├── __init__.py
│   └── abdm_gateway_client.py                       ← HTTP client, reads facility_id + gateway_api_key from settings
│
├── tools/
│   ├── __init__.py
│   └── m1/
│       ├── __init__.py
│       ├── models.py                                ← Pydantic input models for all M1 tools
│       ├── abha_enrollment_tools.py                 ← 6 tools
│       ├── abha_verification_tools.py               ← 2 tools
│       ├── abha_address_verification_tools.py       ← 3 tools
│       └── find_abha_tools.py                       ← 8 tools
│
└── services/
    ├── __init__.py
    └── m1/
        ├── __init__.py
        ├── abha_enrollment_service.py
        ├── abha_verification_service.py
        ├── abha_address_verification_service.py
        └── find_abha_service.py
```

---

## Request Flow

```
Agent calls tool "aadhaar_enrollment_init"
          ↓
FastMCP routes to aadhaar_enrollment_init(request)
          ↓
AbhaEnrollmentService(client).aadhaar_enrollment_init(aadhaar_number)
          ↓
ABDMGatewayClient sends to Go backend
  POST /api/v1/registration/aadhaar/init
  Authorization: Bearer <gateway_api_key>     ← from settings
  X-Facility-ID: <facility_id>                ← from settings
          ↓
Go backend validates key, runs handler, returns response
          ↓
response flows back: client → service → tool → FastMCP → agent
```

---

## Task 1: Project Scaffold

- [ ] **Step 1: Create `requirements.txt`**

```
fastmcp>=2.0.0
httpx>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
```

- [ ] **Step 2: Create `.env.example`**

```
ABDM_GATEWAY_BASE_URL=http://localhost:8080
ABDM_GATEWAY_TIMEOUT=30
ABDM_FACILITY_ID=your-facility-id
ABDM_GATEWAY_API_KEY=your-backend-api-key
```

- [ ] **Step 3: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
*.pyo
.venv/
venv/
dist/
*.egg-info/
```

- [ ] **Step 4: Create `config/settings.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ABDM_",
        extra="ignore"
    )

    gateway_base_url: str = Field(default="http://localhost:8080")
    gateway_timeout: int = Field(default=30)
    facility_id: str = Field(default="")
    gateway_api_key: str = Field(default="")


settings = Settings()
```

- [ ] **Step 5: Create `config/__init__.py`**

```python
from .settings import settings

__all__ = ["settings"]
```

- [ ] **Step 6: Create empty `__init__.py` files**

```
clients/__init__.py
tools/__init__.py
tools/m1/__init__.py
services/__init__.py
services/m1/__init__.py
```

- [ ] **Step 7: Install dependencies**

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
```

- [ ] **Step 8: Commit**

```bash
git add .
git commit -m "chore: project scaffold"
```

---

## Task 2: ABDM Gateway HTTP Client

- [ ] **Step 1: Create `clients/abdm_gateway_client.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add clients/
git commit -m "feat: ABDM gateway HTTP client"
```

---

## Task 3: Pydantic Input Models

- [ ] **Step 1: Create `tools/m1/models.py`**

```python
from typing import Optional
from pydantic import BaseModel, Field


# ── Aadhaar Enrollment ──────────────────────────────────────────────────────

class AadhaarEnrollmentInitInput(BaseModel):
    aadhaar_number: str = Field(..., description="12-digit Aadhaar number of the patient")


class AadhaarEnrollmentVerifyOTPInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID returned from aadhaar_enrollment_init")
    otp: str = Field(..., description="OTP received on the Aadhaar-linked mobile number")
    mobile: str = Field(..., description="10-digit mobile number of the patient")


class AadhaarEnrollmentVerifyMobileOTPInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID from the previous enrollment step")
    otp: str = Field(..., description="OTP received on the patient's mobile number")


class UserDetailInput(BaseModel):
    first_name: str = Field(default="", description="Patient's first name")
    last_name: str = Field(default="", description="Patient's last name")
    day_of_birth: str = Field(default="", description="Day of birth (DD)")
    month_of_birth: str = Field(default="", description="Month of birth (MM)")
    year_of_birth: str = Field(default="", description="Year of birth (YYYY)")


class AadhaarEnrollmentSuggestAddressInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID from the previous enrollment step")
    user_detail: UserDetailInput = Field(
        default_factory=UserDetailInput,
        description="Patient name and date of birth for generating ABHA address suggestions"
    )


class AadhaarEnrollmentCreateAddressInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID from the previous enrollment step")
    abha_address: str = Field(
        ..., description="Chosen ABHA address from the suggestions list (without @abdm suffix)"
    )


class EnrollABHAByBiometricInput(BaseModel):
    aadhaar_number: str = Field(..., description="12-digit Aadhaar number of the patient")
    pid: str = Field(..., description="Biometric PID block captured from the biometric device")
    mobile_number: str = Field(..., description="10-digit mobile number of the patient")


# ── ABHA Verification ───────────────────────────────────────────────────────

class VerifyABHAInitInput(BaseModel):
    method: str = Field(
        ...,
        description=(
            "Verification method. One of: "
            "'aadhaar_otp' (Aadhaar number, OTP via UIDAI), "
            "'abha_number_aadhaar_otp' (ABHA number, OTP via UIDAI), "
            "'abha_number_abha_otp' (ABHA number, OTP via ABDM), "
            "'mobile_otp' (mobile number, OTP via ABDM)"
        )
    )
    identifier: str = Field(
        ...,
        description=(
            "The identifier matching the chosen method: "
            "12-digit Aadhaar for aadhaar_otp, "
            "ABHA number (91-xxxx-xxxx-xxxx) for abha_number_* methods, "
            "10-digit mobile for mobile_otp"
        )
    )


class VerifyABHAConfirmInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID returned from verify_abha_init")
    otp: Optional[str] = Field(
        default=None,
        description="OTP received by the patient. Provide for the OTP verification step."
    )
    abha_number: Optional[str] = Field(
        default=None,
        description=(
            "ABHA number to select when multiple accounts are returned (skip_state=abha_select). "
            "Leave empty for the OTP step."
        )
    )


# ── ABHA Address Verification ───────────────────────────────────────────────

class SearchABHAAddressAuthMethodsInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address to look up (e.g. patient@abdm)")


class ABHAAddressVerificationInitInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address to verify (e.g. patient@abdm)")
    method: str = Field(
        ..., description="Auth method to use for verification. One of: 'mobile', 'aadhaar'"
    )


class ABHAAddressVerificationConfirmInput(BaseModel):
    txn_id: str = Field(
        ..., description="Transaction ID returned from abha_address_verification_init"
    )
    otp: str = Field(
        ..., description="OTP received by the patient on their registered mobile/Aadhaar"
    )


# ── Find ABHA ───────────────────────────────────────────────────────────────

class SearchABHAInput(BaseModel):
    mobile: str = Field(..., description="10-digit mobile number to search ABHA profiles by")


class FindABHAInitInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID returned from search_abha")
    index: str = Field(
        ..., description="Index of the ABHA profile selected from the search_abha results"
    )
    otp_system: str = Field(
        ..., description="OTP delivery system. One of: 'abdm', 'aadhaar'"
    )


class FindABHAVerifyInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID from find_abha_init")
    otp: str = Field(..., description="OTP received by the patient")


class GetABHAProfileInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address of the patient (e.g. patient@abdm)")


class GetABHAQRInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address of the patient to fetch QR code for")


class GetABHACardInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address of the patient to fetch ABHA card for")


class SessionInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address of the patient (e.g. patient@abdm)")
```

- [ ] **Step 2: Commit**

```bash
git add tools/m1/models.py
git commit -m "feat: Pydantic input models for all M1 MCP tools"
```

---

## Task 4: Service Layer — M1

- [ ] **Step 1: Create `services/m1/abha_enrollment_service.py`**

```python
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
```

- [ ] **Step 2: Create `services/m1/abha_verification_service.py`**

```python
from typing import Any, Dict, Optional
from clients.abdm_gateway_client import ABDMGatewayClient


class AbhaVerificationService:
    def __init__(self, client: ABDMGatewayClient):
        self._client = client

    async def verify_abha_init(self, method: str, identifier: str) -> Dict[str, Any]:
        return await self._client.verify_abha_init(method, identifier)

    async def verify_abha_confirm(self, txn_id: str, otp: Optional[str], abha_number: Optional[str]) -> Dict[str, Any]:
        return await self._client.verify_abha_confirm(txn_id, otp, abha_number)
```

- [ ] **Step 3: Create `services/m1/abha_address_verification_service.py`**

```python
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
```

- [ ] **Step 4: Create `services/m1/find_abha_service.py`**

```python
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
```

- [ ] **Step 5: Commit**

```bash
git add services/
git commit -m "feat: M1 service layer"
```

---

## Task 5: MCP Tools — ABHA Enrollment

- [ ] **Step 1: Create `tools/m1/abha_enrollment_tools.py`**

```python
from typing import Any, Dict
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.abha_enrollment_service import AbhaEnrollmentService
from tools.m1.models import (
    AadhaarEnrollmentInitInput,
    AadhaarEnrollmentVerifyOTPInput,
    AadhaarEnrollmentVerifyMobileOTPInput,
    AadhaarEnrollmentSuggestAddressInput,
    AadhaarEnrollmentCreateAddressInput,
    EnrollABHAByBiometricInput,
)

_client = ABDMGatewayClient()
_service = AbhaEnrollmentService(_client)


def register_abha_enrollment_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_init(request: AadhaarEnrollmentInitInput) -> Dict[str, Any]:
        """
        Start ABHA enrollment using Aadhaar. Sends an OTP to the Aadhaar-linked mobile number.
        Step 1 of the Aadhaar enrollment flow. Returns txn_id for the next step.
        Call aadhaar_enrollment_verify_otp next.
        """
        return await _service.aadhaar_enrollment_init(request.aadhaar_number)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_verify_otp(request: AadhaarEnrollmentVerifyOTPInput) -> Dict[str, Any]:
        """
        Verify the Aadhaar OTP to continue enrollment. Step 2 of the Aadhaar enrollment flow.

        Returns txn_id and skip_state:
        - 'confirm_mobile_otp' → call aadhaar_enrollment_verify_mobile_otp
        - 'abha_end' → enrollment complete, profile returned
        - 'abha_select' → multiple existing ABHA accounts, show to user
        - 'abha_create' → call aadhaar_enrollment_suggest_address
        """
        return await _service.aadhaar_enrollment_verify_otp(request.txn_id, request.otp, request.mobile)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_verify_mobile_otp(request: AadhaarEnrollmentVerifyMobileOTPInput) -> Dict[str, Any]:
        """
        Verify mobile OTP during Aadhaar enrollment. Called when skip_state is 'confirm_mobile_otp'.
        Returns txn_id and updated skip_state.
        """
        return await _service.aadhaar_enrollment_verify_mobile_otp(request.txn_id, request.otp)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def aadhaar_enrollment_suggest_address(request: AadhaarEnrollmentSuggestAddressInput) -> Dict[str, Any]:
        """
        Get ABHA address suggestions for the patient. Called when skip_state is 'abha_create'.
        Returns a list of suggested ABHA addresses.
        Pass the chosen address to aadhaar_enrollment_create_address.
        """
        return await _service.aadhaar_enrollment_suggest_address(request.txn_id, request.user_detail.model_dump())

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def aadhaar_enrollment_create_address(request: AadhaarEnrollmentCreateAddressInput) -> Dict[str, Any]:
        """
        Create the ABHA address — final step of Aadhaar enrollment.
        Pass the abha_address chosen from aadhaar_enrollment_suggest_address results.
        Returns the complete ABHA profile with token on success.
        """
        return await _service.aadhaar_enrollment_create_address(request.txn_id, request.abha_address)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def enroll_abha_by_biometric(request: EnrollABHAByBiometricInput) -> Dict[str, Any]:
        """
        Enroll a patient for ABHA using biometric authentication (fingerprint/iris via UIDAI).
        Use instead of the OTP flow when a biometric device is available.
        Returns the complete ABHA profile on success.
        """
        return await _service.enroll_abha_by_biometric(request.aadhaar_number, request.pid, request.mobile_number)
```

- [ ] **Step 2: Commit**

```bash
git add tools/m1/abha_enrollment_tools.py
git commit -m "feat: ABHA enrollment MCP tools (6 tools)"
```

---

## Task 6: MCP Tools — ABHA Verification

- [ ] **Step 1: Create `tools/m1/abha_verification_tools.py`**

```python
from typing import Any, Dict
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.abha_verification_service import AbhaVerificationService
from tools.m1.models import VerifyABHAInitInput, VerifyABHAConfirmInput

_client = ABDMGatewayClient()
_service = AbhaVerificationService(_client)


def register_abha_verification_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def verify_abha_init(request: VerifyABHAInitInput) -> Dict[str, Any]:
        """
        Initiate ABHA verification. Sends an OTP to the patient based on the chosen method.

        Methods:
        - 'aadhaar_otp': Aadhaar number, OTP via UIDAI
        - 'abha_number_aadhaar_otp': ABHA number, OTP via UIDAI
        - 'abha_number_abha_otp': ABHA number, OTP via ABDM
        - 'mobile_otp': mobile number, OTP via ABDM (may return multiple accounts)

        Returns txn_id. Call verify_abha_confirm next with the OTP.
        """
        return await _service.verify_abha_init(request.method, request.identifier)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    async def verify_abha_confirm(request: VerifyABHAConfirmInput) -> Dict[str, Any]:
        """
        Confirm ABHA verification with OTP, or select an account when multiple are returned.

        OTP step: provide txn_id + otp (leave abha_number empty).
        Account selection (skip_state='abha_select'): provide txn_id + abha_number (leave otp empty).

        Returns profile on success (skip_state='abha_end') or abha_profiles list for selection.
        """
        return await _service.verify_abha_confirm(request.txn_id, request.otp, request.abha_number)
```

- [ ] **Step 2: Commit**

```bash
git add tools/m1/abha_verification_tools.py
git commit -m "feat: ABHA verification MCP tools (2 tools)"
```

---

## Task 7: MCP Tools — ABHA Address Verification

- [ ] **Step 1: Create `tools/m1/abha_address_verification_tools.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add tools/m1/abha_address_verification_tools.py
git commit -m "feat: ABHA address verification MCP tools (3 tools)"
```

---

## Task 8: MCP Tools — Find ABHA, Profile, Session

- [ ] **Step 1: Create `tools/m1/find_abha_tools.py`**

```python
import base64
from typing import Any, Dict
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from clients.abdm_gateway_client import ABDMGatewayClient
from services.m1.find_abha_service import FindAbhaService
from tools.m1.models import (
    SearchABHAInput, FindABHAInitInput, FindABHAVerifyInput,
    GetABHAProfileInput, GetABHAQRInput, GetABHACardInput, SessionInput,
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
```

- [ ] **Step 2: Commit**

```bash
git add tools/m1/find_abha_tools.py
git commit -m "feat: Find ABHA, profile, QR, card, and session MCP tools (8 tools)"
```

---

## Task 9: Server Entry Point

- [ ] **Step 1: Create `server.py`**

```python
import argparse
import logging
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from tools.m1.abha_enrollment_tools import register_abha_enrollment_tools
from tools.m1.abha_verification_tools import register_abha_verification_tools
from tools.m1.abha_address_verification_tools import register_abha_address_verification_tools
from tools.m1.find_abha_tools import register_find_abha_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    mcp = FastMCP(
        name="ABDM Compliance Gateway",
        stateless_http=True,
        instructions="""
            MCP server for the ABDM Compliance Gateway.
            Provides tools for managing ABHA (Ayushman Bharat Health Account) for patients.

            Available flows:
            - ABHA Enrollment: Create a new ABHA using Aadhaar OTP or biometric.
            - ABHA Verification: Verify an existing ABHA number using OTP.
            - ABHA Address Verification: Verify an ABHA address (e.g. patient@abdm).
            - Find ABHA: Search and retrieve an ABHA profile by mobile number.
            - Profile and Assets: Fetch ABHA profile, QR code, and health card.
            - Session: Manage active ABDM sessions.
        """
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    register_abha_enrollment_tools(mcp)
    register_abha_verification_tools(mcp)
    register_abha_address_verification_tools(mcp)
    register_find_abha_tools(mcp)

    return mcp


def main():
    parser = argparse.ArgumentParser(description="ABDM MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="http")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()

    logger.info(f"Starting ABDM MCP Server ({args.transport} transport)")
    mcp = create_mcp_server()

    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify server starts**

```bash
python server.py --transport http --port 8888
# Expected: Uvicorn running on http://localhost:8888
```

- [ ] **Step 3: Verify health**

```bash
curl http://localhost:8888/health
# Expected: OK
```

- [ ] **Step 4: Commit**

```bash
git add server.py
git commit -m "feat: FastMCP server entry point with all M1 tools"
```

---

## Task 10: README

- [ ] **Step 1: Create `README.md` and commit**

```bash
git add README.md
git commit -m "docs: README with setup and tool reference"
git push origin main
```

---

## Self-Review

- ✅ No auth layer — tool discovery is the MCP client's responsibility
- ✅ `facility_id` + `gateway_api_key` are static config in `.env` — instance is the identity
- ✅ `ABDMGatewayClient` instantiated once per tool file as module-level singleton
- ✅ Tools are dead simple: input model → service call → return result
- ✅ M2-ready: `tools/m1/`, `services/m1/` — new milestones add new folders
- ✅ Both `http` and `stdio` transport supported
