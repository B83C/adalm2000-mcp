from __future__ import annotations

import numpy as np

from adalm2000_mcp.backend import Backend


def handle_scope(
    backend: Backend,
    operation: str,
    channel: int = 1,
    sample_count: int = 8192,
    sample_rate: float | None = None,
) -> dict:
    if operation == "capture":
        data = backend.scope_capture(channel, sample_count, sample_rate)
        return {
            "success": True,
            "channel": channel,
            "sample_rate": data.sample_rate,
            "time_span": data.time_span,
            "vpp": data.vpp,
            "vmin": data.vmin,
            "vmax": data.vmax,
            "frequency": data.frequency,
            "samples": data.samples[:1024],
            "total_samples": len(data.samples),
        }

    elif operation == "fft":
        data = backend.scope_capture(channel, sample_count, sample_rate)
        sig = np.array(data.samples)
        n = len(sig)
        window = np.hamming(n)
        sig_w = sig * window
        fft_vals = np.fft.rfft(sig_w)
        fft_mag = np.abs(fft_vals) / n
        freqs = np.fft.rfftfreq(n, d=1.0 / data.sample_rate)
        peak_idx = int(np.argmax(fft_mag[1:])) + 1
        return {
            "success": True,
            "channel": channel,
            "sample_rate": data.sample_rate,
            "peak_freq_hz": float(freqs[peak_idx]),
            "peak_magnitude": float(fft_mag[peak_idx]),
            "bins": [{"freq": float(f), "mag": float(m)} for f, m in zip(freqs[:512].tolist(), fft_mag[:512].tolist())],
            "total_bins": len(freqs),
        }

    elif operation == "measure":
        data = backend.scope_capture(channel, sample_count, sample_rate)
        sig = np.array(data.samples)
        rms = float(np.sqrt(np.mean(sig ** 2)))
        return {
            "success": True,
            "channel": channel,
            "vpp": data.vpp,
            "vmin": data.vmin,
            "vmax": data.vmax,
            "vrms": rms,
            "frequency": data.frequency,
        }

    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}
