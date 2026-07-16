from __future__ import annotations

from adalm2000_mcp.backend import OUTPUT_MODES, PULL_MODES, WAVEFORM_TYPES, Backend, PatternConfig


def handle_pattern(
    backend: Backend,
    operation: str,
    channel: int = 0,
    waveform: str = "square",
    frequency: float = 1000.0,
    duty_cycle: float = 50.0,
    data: str = "",
    sample_rate: float = 100e6,
    output_mode: str = "push_pull",
    pull_mode: str = "none",
    burst_count: int = 0,
    invert: bool = False,
) -> dict:
    if operation == "generate":
        if waveform not in WAVEFORM_TYPES:
            return {"success": False, "error": f"Unknown waveform: {waveform}. Choose: {', '.join(WAVEFORM_TYPES)}"}
        if output_mode not in OUTPUT_MODES:
            return {"success": False, "error": f"Unknown output mode: {output_mode}. Choose: {', '.join(OUTPUT_MODES)}"}
        if pull_mode not in PULL_MODES:
            return {"success": False, "error": f"Unknown pull mode: {pull_mode}. Choose: {', '.join(PULL_MODES)}"}
        parsed_data = [int(x.strip(), 0) for x in data.split(",") if x.strip()] if data else None
        cfg = PatternConfig(
            channel=channel, waveform=waveform, frequency=frequency,
            duty_cycle=duty_cycle, data=parsed_data, sample_rate=sample_rate,
            output_mode=output_mode, pull_mode=pull_mode,
            burst_count=burst_count, invert=invert,
        )
        ok = backend.pattern_generate(cfg)
        return {
            "success": ok,
            "message": f"Pattern ch{channel}: {waveform}" if ok else f"Failed on ch{channel}",
            "config": {
                "channel": channel, "waveform": waveform, "frequency": frequency,
                "duty_cycle": duty_cycle, "sample_rate": sample_rate,
                "output_mode": output_mode, "pull_mode": pull_mode,
                "burst_count": burst_count, "invert": invert,
            },
        }

    elif operation == "stop":
        ok = backend.pattern_stop(channel)
        return {"success": ok, "message": f"Pattern ch{channel} stopped" if ok else f"Failed to stop ch{channel}"}

    elif operation == "status":
        configs = backend.pattern_status()
        return {
            "success": True,
            "channels": [
                {
                    "channel": c.channel, "waveform": c.waveform,
                    "frequency": c.frequency, "duty_cycle": c.duty_cycle,
                    "output_mode": c.output_mode, "pull_mode": c.pull_mode,
                    "burst_count": c.burst_count, "invert": c.invert,
                    "enabled": c.enabled,
                }
                for c in configs
            ],
        }

    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}
