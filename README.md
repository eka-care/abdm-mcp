# ABDM MCP Server

MCP server for the [ABDM Compliance Gateway](https://github.com/eka-care/abdm).
Exposes ABDM M1 flows as MCP tools callable by AI agents.

## Prerequisites

- Python 3.11+
- A running [ABDM Compliance Gateway](https://github.com/eka-care/abdm) instance

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your gateway URL, facility ID, and backend API key.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `ABDM_GATEWAY_BASE_URL` | URL of the ABDM Compliance Gateway (Go server) | `http://localhost:8080` |
| `ABDM_GATEWAY_TIMEOUT` | HTTP timeout in seconds | `30` |
| `ABDM_FACILITY_ID` | Facility ID sent to the Go backend | `""` |
| `ABDM_GATEWAY_API_KEY` | API key for the Go backend's `/api/v1` routes | `""` |

## Flow Enforcement

The MCP server enforces correct tool call sequencing per session. Calling a tool
out of order (e.g. `aadhaar_enrollment_verify_otp` without first calling
`aadhaar_enrollment_init`) returns a descriptive error telling the agent which
tool must be called first.

### Transport requirements

| Transport | Session support | State storage |
|---|---|---|
| stdio | Single session (in-memory) | Python dict |
| Stateful HTTP | `mcp-session-id` per session | Redis |
| Stateless HTTP | None | Not supported |

**Production deployments must use stateful HTTP or stdio.**
Stateless HTTP (`stateless_http=True`) does not carry a session ID and cannot
enforce flow ordering.

### Redis configuration (stateful HTTP only)

Set `ABDM_REDIS_URL` in `.env`:

```env
ABDM_REDIS_URL=redis://localhost:6379
```

If `ABDM_REDIS_URL` is empty, the server falls back to in-memory state
(suitable for single-instance deployments).

## Run

```bash
# HTTP transport (remote AI agents)
python server.py --transport http --host 0.0.0.0 --port 8888

# stdio transport (Claude Desktop or local agents)
python server.py --transport stdio
```

## Available Tools (M1)

### ABHA Enrollment (Aadhaar OTP flow)
1. `aadhaar_enrollment_init` — send OTP to Aadhaar-linked mobile
2. `aadhaar_enrollment_verify_otp` — verify OTP, get skip_state
3. `aadhaar_enrollment_verify_mobile_otp` — verify mobile OTP (if skip_state = confirm_mobile_otp)
4. `aadhaar_enrollment_suggest_address` — get ABHA address suggestions (if skip_state = abha_create)
5. `aadhaar_enrollment_create_address` — create chosen ABHA address

### ABHA Enrollment (Biometric)
- `enroll_abha_by_biometric` — single-step enrollment using biometric PID block

### ABHA Verification
1. `verify_abha_init` — send OTP via chosen method (aadhaar_otp, abha_number_otp, mobile_otp)
2. `verify_abha_confirm` — verify OTP or select account

### ABHA Address Verification
1. `search_abha_address_auth_methods` — get available auth methods for an ABHA address
2. `abha_address_verification_init` — send OTP
3. `abha_address_verification_confirm` — verify OTP

### Find ABHA
1. `search_abha` — search profiles by mobile number
2. `find_abha_init` — send OTP for selected profile
3. `find_abha_verify` — verify OTP, get profile + session token

### Profile and Assets
- `get_abha_profile` — fetch ABHA profile by ABHA address
- `get_abha_qr` — fetch QR code as base64-encoded PNG
- `get_abha_card` — fetch health card as base64-encoded file

### Session
- `get_session` — get active ABDM session for an ABHA address
- `invalidate_session` — delete active session
