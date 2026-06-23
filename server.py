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
        mcp.run(transport="http", host=args.host, port=args.port, stateless_http=True)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
