from __future__ import annotations

from adalm2000_mcp.backend import Backend, PatternConfig

WAVEFORM_TYPES = ["square", "pulse", "clock", "constant", "custom"]


def handle_pattern(
    backend: Backend,
    operation: str,
    channel: int = 0,
    waveform: str = "square",
    frequency: float = 1000.0,
    duty_cycle: float = 50.0,
    data: str = "",
    sample_rate: float = 100e6,
    open_drain: bool = False,
) -> dict:
    if operation == "generate":
        if waveform not in WAVEFORM_TYPES:
            return {"success": False, "error": f"Unknown waveform: {waveform}. Choose: {', '.join(WAVEFORM_TYPES)}"}
        parsed_data = [int(x.strip(), 0) for x in data.split(",") if x.strip()] if data else None
        cfg = PatternConfig(
            channel=channel, waveform=waveform, frequency=frequency,
            duty_cycle=duty_cycle, data=parsed_data, sample_rate=sample_rate,
            open_drain=open_drain,
        )
        ok = backend.pattern_generate(cfg)
        return {
            "success": ok,
            "message": f"Pattern generator channel {channel}: {waveform}" if ok else f"Failed to start channel {channel}",
            "config": {
                "channel": channel, "waveform": waveform, "frequency": frequency,
                "duty_cycle": duty_cycle, "sample_rate": sample_rate,
                "open_drain": open_drain,
            },
        }

    elif operation == "stop":
        ok = backend.pattern_stop(channel)
        return {"success": ok, "message": f"Pattern channel {channel} stopped" if ok else f"Failed to stop channel {channel}"}

    elif operation == "status":
        configs = backend.pattern_status()
        return {
            "success": True,
            "channels": [
                {
                    "channel": c.channel, "waveform": c.waveform,
                    "frequency": c.frequency, "duty_cycle": c.duty_cycle,
                    "open_drain": c.open_drain, "enabled": c.enabled,
                }
                for c in configs
            ],
        }

    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}
