from __future__ import annotations

import os

from fastmcp import FastMCP

from adalm2000_mcp.backend import Backend, create_backend
from adalm2000_mcp.tools.device import handle_device
from adalm2000_mcp.tools.awg import handle_awg
from adalm2000_mcp.tools.scope import handle_scope
from adalm2000_mcp.tools.psu import handle_psu

mcp = FastMCP("adalm2000-mcp", version="0.1.0")

_backend: Backend | None = None


def get_backend() -> Backend:
    global _backend
    if _backend is None:
        mock = os.environ.get("ADALM_MCP_MOCK", "auto").lower()
        _backend = create_backend(mock=mock in ("true", "1", "enable", "force"))
    return _backend


def set_backend(b: Backend) -> None:
    global _backend
    _backend = b


@mcp.tool()
def adalm_device(operation: str) -> dict:
    b = get_backend()
    return handle_device(b, operation)


@mcp.tool()
def adalm_awg(
    operation: str,
    channel: int = 1,
    waveform: str = "sine",
    frequency: float = 1000.0,
    amplitude: float = 1.0,
    offset: float = 0.0,
) -> dict:
    b = get_backend()
    return handle_awg(b, operation, channel, waveform, frequency, amplitude, offset)


@mcp.tool()
def adalm_scope(
    operation: str,
    channel: int = 1,
    sample_count: int = 8192,
    sample_rate: float | None = None,
) -> dict:
    b = get_backend()
    return handle_scope(b, operation, channel, sample_count, sample_rate)


@mcp.tool()
def adalm_psu(operation: str, channel: int = 0, voltage: float = 0.0) -> dict:
    b = get_backend()
    return handle_psu(b, operation, channel, voltage)


def run_server(mock: bool = False, http: bool = False, port: int = 10892, transport: str | None = None):
    if mock:
        os.environ["ADALM_MCP_MOCK"] = "force"
    _transport = transport or ("http" if http else "stdio")
    if _transport == "http":
        mcp.run(transport="sse", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
