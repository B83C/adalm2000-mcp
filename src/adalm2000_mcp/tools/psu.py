from __future__ import annotations

from adalm2000_mcp.backend import Backend


def handle_psu(backend: Backend, operation: str, channel: int = 0, voltage: float = 0.0) -> dict:
    if channel not in (0, 1):
        return {"success": False, "error": "PSU channels: 0 (V+) or 1 (V-)"}

    if operation == "set":
        if voltage < -5 or voltage > 5:
            return {"success": False, "error": "Voltage must be between -5 and +5 V"}
        ok = backend.psu_set(channel, voltage)
        return {"success": ok, "message": f"PSU channel {channel} set to {voltage}V", "channel": channel, "voltage": voltage}

    elif operation == "get":
        v = backend.psu_get(channel)
        return {"success": True, "channel": channel, "voltage": v}

    elif operation == "enable":
        ok = backend.psu_enable(channel)
        label = "V+" if channel == 0 else "V-"
        return {"success": ok, "message": f"PSU {label} enabled"}

    elif operation == "disable":
        ok = backend.psu_disable(channel)
        label = "V+" if channel == 0 else "V-"
        return {"success": ok, "message": f"PSU {label} disabled"}

    elif operation == "status":
        return {
            "success": True,
            "channels": [
                {"channel": 0, "label": "V+", "voltage": backend.psu_get(0)},
                {"channel": 1, "label": "V-", "voltage": backend.psu_get(1)},
            ],
        }

    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}
