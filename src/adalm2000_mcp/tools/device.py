from __future__ import annotations

from adalm2000_mcp.backend import Backend


def handle_device(backend: Backend, operation: str) -> dict:
    if operation == "list":
        devs = backend.list_devices()
        return {"success": True, "devices": devs}

    elif operation == "connect":
        info = backend.connect()
        return {
            "success": info.connected,
            "message": f"Connected to {info.name}",
            "device": {
                "serial": info.serial,
                "name": info.name,
                "mock": info.mock,
                "channels_scope": info.channels_scope,
                "channels_awg": info.channels_awg,
                "psu": info.psu,
            },
        }

    elif operation == "disconnect":
        ok = backend.disconnect()
        return {"success": ok, "message": "Disconnected"}

    elif operation == "status":
        info = backend.status()
        return {
            "success": True,
            "connected": info.connected,
            "serial": info.serial,
            "name": info.name,
            "mock": info.mock,
        }

    elif operation == "check":
        devs = backend.list_devices()
        info = backend.status()
        return {
            "success": info.connected or len(devs) > 0,
            "devices": devs,
            "mock": info.mock,
        }

    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}
