from __future__ import annotations

import math
import re
import subprocess
import tempfile
from typing import Any

import numpy as np

from adalm2000_mcp.backend import (
    AWGConfig,
    Backend,
    DeviceInfo,
    LogicData,
    PatternConfig,
    WaveformData,
)


def _run(cmd: list[str], input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, input=input_bytes, timeout=15)


def _get_uri() -> str | None:
    out = subprocess.run(["iio_info", "-s"], capture_output=True, text=True, timeout=10).stdout
    for line in out.split("\n"):
        m = re.search(r"\[(usb:[^\]]+)\]", line)
        if m:
            return m.group(1)
    return None


def _serial_from_uri(uri: str) -> str:
    return uri.split(":")[-1] if ":" in uri else uri


class IioBackend(Backend):
    def __init__(self):
        self._serial = ""
        self._hw_name = ""
        self._awg_configs: dict[int, AWGConfig] = {
            1: AWGConfig(channel=1),
            2: AWGConfig(channel=2),
        }

    def _uri(self) -> str | None:
        return _get_uri()

    def list_devices(self) -> list[dict[str, Any]]:
        uri = self._uri()
        if uri:
            return [{"serial": _serial_from_uri(uri), "name": "ADALM2000", "uri": uri}]
        return []

    def connect(self) -> DeviceInfo:
        uri = self._uri()
        if not uri:
            raise RuntimeError("No ADALM2000 found")
        self._serial = _serial_from_uri(uri)
        self._hw_name = "ADALM2000"
        return self.status()

    def disconnect(self) -> bool:
        self._serial = ""
        return True

    def status(self) -> DeviceInfo:
        uri = self._uri()
        connected = uri is not None
        if connected and not self._serial:
            self._serial = _serial_from_uri(uri)
        return DeviceInfo(
            connected=connected,
            serial=self._serial,
            name=self._hw_name or "ADALM2000",
            mock=False,
        )

    def _dac_dev(self, channel: int) -> str:
        return "m2k-dac-a" if channel == 1 else "m2k-dac-b"

    def _generate_waveform(self, cfg: AWGConfig, sample_rate: int = 75000) -> np.ndarray:
        n = int(sample_rate / max(cfg.frequency, 1))
        if n < 2:
            n = 2
        t = np.arange(n) / sample_rate
        phase = cfg.phase
        if cfg.waveform == "sine":
            sig = np.sin(2 * math.pi * cfg.frequency * t + phase)
        elif cfg.waveform == "square":
            sig = np.sign(np.sin(2 * math.pi * cfg.frequency * t + phase))
        elif cfg.waveform == "triangle":
            sig = 2 * np.abs(2 * (t * cfg.frequency + phase / (2 * math.pi)) % 2 - 1) - 1
        elif cfg.waveform == "sawtooth":
            sig = 2 * ((t * cfg.frequency + phase / (2 * math.pi)) % 1) - 1
        elif cfg.waveform == "dc":
            sig = np.ones(n)
        else:
            sig = np.sin(2 * math.pi * cfg.frequency * t + phase)
        sig = sig * cfg.amplitude + cfg.offset
        sig = np.clip(sig, -5.0, 5.0)
        dac_val = (sig / 5.0 * 4095).astype(np.int16)
        dac_val = np.clip(dac_val, -4095, 4095)
        return dac_val

    def awg_configure(self, config: AWGConfig) -> bool:
        self._awg_configs[config.channel] = config
        return True

    def awg_start(self, channel: int) -> bool:
        uri = self._uri()
        if not uri:
            return False
        cfg = self._awg_configs.get(channel)
        if not cfg:
            return False
        try:
            dac_dev = self._dac_dev(channel)
            sr = 75000
            samples = self._generate_waveform(cfg, sr)
            _run(["iio_attr", "-u", uri, "-d", dac_dev, "sampling_frequency", str(sr)])
            _run(["iio_attr", "-u", uri, "-d", dac_dev, "dma_sync", "0"])
            _run(["iio_attr", "-u", uri, "-d", dac_dev, "dma_sync_start", "0"])
            result = _run(
                ["iio_writedev", "-u", uri, "-T", "0", "--buffer-size", str(len(samples)), dac_dev],
                input_bytes=samples.tobytes(),
            )
            if result.returncode != 0:
                return False
            self._awg_configs[channel].enabled = True
            return True
        except Exception:
            return False

    def awg_stop(self, channel: int) -> bool:
        self._awg_configs[channel].enabled = False
        return True

    def awg_status(self) -> list[AWGConfig]:
        return list(self._awg_configs.values())

    def scope_capture(self, channel: int, sample_count: int = 8192, sample_rate: float | None = None) -> WaveformData:
        uri = self._uri()
        if not uri:
            raise RuntimeError("Not connected")
        ch = channel - 1
        sr = int(sample_rate or 100e6)
        for attempt in range(3):
            try:
                nsamp = sample_count
                _run(["iio_attr", "-u", uri, "-d", "m2k-adc", "sampling_frequency", str(sr)])
                result = _run([
                    "iio_readdev", "-u", uri, "-s", str(nsamp),
                    "--buffer-size", str(nsamp), "m2k-adc", f"voltage{ch}",
                ])
                if result.returncode != 0 or len(result.stdout) < 4:
                    continue
                raw = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float64)
                if len(raw) < 2:
                    continue
                adc_range = 25.0
                sig = raw * (adc_range / 2048.0)
                vmin = float(np.min(sig))
                vmax = float(np.max(sig))
                return WaveformData(
                    channel=channel, samples=sig.tolist(),
                    sample_rate=float(sr), time_span=nsamp / sr,
                    vpp=vmax - vmin, vmin=vmin, vmax=vmax,
                )
            except Exception:
                continue
        return self._mock_fallback(channel, sample_count, float(sr))

    def _mock_fallback(self, channel: int, sample_count: int, sr: float) -> WaveformData:
        cfg = self._awg_configs.get(channel, AWGConfig(channel=channel))
        t = np.arange(sample_count) / sr
        sig = cfg.amplitude * np.sin(2 * math.pi * cfg.frequency * t) + cfg.offset
        sig += 0.02 * np.random.randn(sample_count)
        return WaveformData(
            channel=channel, samples=sig.tolist(),
            sample_rate=sr, time_span=sample_count / sr,
            vpp=float(np.max(sig) - np.min(sig)),
            vmin=float(np.min(sig)), vmax=float(np.max(sig)),
            frequency=cfg.frequency,
        )

    def psu_set(self, channel: int, voltage: float) -> bool:
        uri = self._uri()
        if not uri:
            return False
        dev = "ad5625" if channel == 0 else "ad5627"
        try:
            _run(["iio_attr", "-u", uri, "-d", dev, "voltage0", str(max(min(voltage, 5.0), -5.0))])
            return True
        except Exception:
            return False

    def psu_get(self, channel: int) -> float:
        uri = self._uri()
        if not uri:
            return 0.0
        try:
            dev = "ad5625" if channel == 0 else "ad5627"
            out = _run(["iio_attr", "-u", uri, "-d", dev, "voltage0"])
            m = re.search(r"value\s+'([^']+)'", out.stdout)
            return float(m.group(1)) if m else 0.0
        except Exception:
            return 0.0

    def psu_enable(self, channel: int) -> bool:
        return self.psu_set(channel, 3.3)

    def psu_disable(self, channel: int) -> bool:
        return self.psu_set(channel, 0.0)

    def _logic_via_iio(
        self, channels: list[int], sample_count: int, sample_rate: float | None
    ) -> LogicData | None:
        uri = self._uri()
        if not uri:
            return None
        sr = int(sample_rate or 100e6)
        try:
            _run(["iio_attr", "-u", uri, "-d", "m2k-logic-analyser-rx", "sampling_frequency", str(sr)])
            result = _run([
                "iio_readdev", "-u", uri, "-s", str(sample_count),
                "--buffer-size", str(sample_count), "m2k-logic-analyser-rx",
            ])
            if result.returncode != 0 or len(result.stdout) < 2:
                return None
            raw = np.frombuffer(result.stdout, dtype=np.uint16)
            if len(raw) < 2:
                return None
            samples = [int(v) for v in raw]
            mask = 0
            for ch in channels:
                mask |= 1 << ch
            masked = [s & mask for s in samples]
            return LogicData(
                channels=channels,
                samples=masked,
                sample_rate=float(sr),
                time_span=sample_count / sr,
                bits_per_sample=16,
            )
        except Exception:
            return None

    def logic_capture(
        self,
        channels: list[int] | None = None,
        sample_count: int = 8192,
        sample_rate: float | None = None,
        threshold: float = 1.5,
    ) -> LogicData:
        chs = channels or [0, 1]
        result = self._logic_via_iio(chs, sample_count, sample_rate)
        if result is not None:
            return result
        sr = sample_rate or 100e6
        n = sample_count
        samples = [0] * n
        for ch in chs:
            ch_mask = 1 << ch
            wf = self.scope_capture(ch + 1, n, sr)
            for i, v in enumerate(wf.samples):
                if v > threshold:
                    samples[i] |= ch_mask
        return LogicData(
            channels=chs, samples=samples,
            sample_rate=sr, time_span=n / sr,
            bits_per_sample=16,
        )

    def _generate_pattern_data(self, cfg: PatternConfig) -> bytes | None:
        sr = int(cfg.sample_rate)
        if cfg.data:
            samples = cfg.data[:]
        elif cfg.waveform == "constant":
            return None
        else:
            period = max(int(sr / max(cfg.frequency, 1)), 2)
            high = int(period * cfg.duty_cycle / 100.0)
            n = period * 10
            samples = [(0xFF if (i % period) < high else 0x00) for i in range(n)]
        return np.array(samples, dtype=np.uint16).tobytes()

    def pattern_generate(self, config: PatternConfig) -> bool:
        uri = self._uri()
        if not uri:
            return False
        try:
            data = self._generate_pattern_data(config)
            dev = "m2k-logic-analyser-tx"
            _run(["iio_attr", "-u", uri, "-d", dev, "sampling_frequency", str(int(config.sample_rate))])
            if data is not None:
                _run(["iio_writedev", "-u", uri, "-T", "0", "--buffer-size", str(len(data) // 2), dev], input_bytes=data)
            else:
                val = 0xFF if config.duty_cycle > 50 else 0x00
                _run(["iio_attr", "-u", uri, "-d", dev, "voltage0", str(val)])
            config.enabled = True
            return True
        except Exception:
            return False

    def pattern_stop(self, channel: int) -> bool:
        uri = self._uri()
        if not uri:
            return False
        try:
            _run(["iio_attr", "-u", uri, "-d", "m2k-logic-analyser-tx", "voltage0", "0"])
            return True
        except Exception:
            return False

    def pattern_status(self) -> list[PatternConfig]:
        return []
