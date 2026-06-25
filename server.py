import argparse
import logging
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from config.settings import settings
from state.memory import InMemoryFlowStateStore
from state.validator import FlowValidator
from tools.m1.abha_enrollment_tools import register_abha_enrollment_tools
from tools.m1.abha_verification_tools import register_abha_verification_tools
from tools.m1.abha_address_verification_tools import register_abha_address_verification_tools
from tools.m1.find_abha_tools import register_find_abha_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_validator(transport: str) -> FlowValidator:
    if transport == "http" and settings.redis_url:
        from state.redis_store import RedisFlowStateStore
        logger.info("Flow state: Redis (%s)", settings.redis_url)
        return FlowValidator(RedisFlowStateStore(settings.redis_url))
    logger.info("Flow state: in-memory (single session)")
    return FlowValidator(InMemoryFlowStateStore())


def create_mcp_server(validator: FlowValidator) -> FastMCP:
    mcp = FastMCP(
        name="ABDM Compliance Gateway",
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

    @mcp.custom_route("/token", methods=["POST"])
    async def token(request: Request) -> JSONResponse:
        return JSONResponse({"access_token": "dummy", "token_type": "bearer", "expires_in": 3600})

    register_abha_enrollment_tools(mcp, validator)
    register_abha_verification_tools(mcp, validator)
    register_abha_address_verification_tools(mcp, validator)
    register_find_abha_tools(mcp, validator)

    return mcp


def main():
    parser = argparse.ArgumentParser(description="ABDM MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="http")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()

    logger.info("Starting ABDM MCP Server (%s transport)", args.transport)
    validator = _build_validator(args.transport)
    mcp = create_mcp_server(validator)

    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
