from __future__ import annotations

from adalm2000_mcp.backend import AWGConfig, Backend

WAVEFORM_TYPES = ["sine", "square", "triangle", "sawtooth", "dc"]


def handle_awg(
    backend: Backend,
    operation: str,
    channel: int = 1,
    waveform: str = "sine",
    frequency: float = 1000.0,
    amplitude: float = 1.0,
    offset: float = 0.0,
) -> dict:
    if operation == "configure":
        if waveform not in WAVEFORM_TYPES:
            return {"success": False, "error": f"Unknown waveform: {waveform}. Choose: {', '.join(WAVEFORM_TYPES)}"}
        cfg = AWGConfig(channel=channel, waveform=waveform, frequency=frequency, amplitude=amplitude, offset=offset)
        ok = backend.awg_configure(cfg)
        return {
            "success": ok,
            "message": f"Channel {channel} configured: {waveform} @ {frequency} Hz, {amplitude} Vpk",
            "config": {"channel": channel, "waveform": waveform, "frequency": frequency, "amplitude": amplitude, "offset": offset},
        }

    elif operation == "start":
        ok = backend.awg_start(channel)
        return {"success": ok, "message": f"AWG channel {channel} started" if ok else f"Failed to start channel {channel}"}

    elif operation == "stop":
        ok = backend.awg_stop(channel)
        return {"success": ok, "message": f"AWG channel {channel} stopped" if ok else f"Failed to stop channel {channel}"}

    elif operation == "status":
        configs = backend.awg_status()
        return {
            "success": True,
            "channels": [
                {"channel": c.channel, "waveform": c.waveform, "frequency": c.frequency, "amplitude": c.amplitude, "offset": c.offset, "enabled": c.enabled}
                for c in configs
            ],
        }

    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}
