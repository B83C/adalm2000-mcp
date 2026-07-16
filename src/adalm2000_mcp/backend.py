from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class DeviceInfo:
    connected: bool
    serial: str = ""
    name: str = ""
    channels_scope: int = 2
    channels_awg: int = 2
    psu: bool = True
    mock: bool = False
    sample_rate_max: float = 100e6
    awg_sample_rate: float = 75e6


@dataclass
class WaveformData:
    channel: int
    samples: list[float]
    sample_rate: float
    time_span: float
    vpp: float
    vmin: float
    vmax: float
    frequency: float | None = None


@dataclass
class AWGConfig:
    channel: int
    waveform: str = "sine"
    frequency: float = 1000.0
    amplitude: float = 1.0
    offset: float = 0.0
    phase: float = 0.0
    duty_cycle: float = 50.0
    enabled: bool = False


@dataclass
class LogicData:
    channels: list[int]
    samples: list[int]
    sample_rate: float
    time_span: float
    bits_per_sample: int = 16


@dataclass
class PatternConfig:
    channel: int
    waveform: str = "square"
    frequency: float = 1000.0
    duty_cycle: float = 50.0
    data: list[int] | None = None
    sample_rate: float = 100e6
    enabled: bool = False


class Backend(ABC):
    @abstractmethod
    def list_devices(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def connect(self) -> DeviceInfo:
        ...

    @abstractmethod
    def disconnect(self) -> bool:
        ...

    @abstractmethod
    def status(self) -> DeviceInfo:
        ...

    @abstractmethod
    def awg_configure(self, config: AWGConfig) -> bool:
        ...

    @abstractmethod
    def awg_start(self, channel: int) -> bool:
        ...

    @abstractmethod
    def awg_stop(self, channel: int) -> bool:
        ...

    @abstractmethod
    def awg_status(self) -> list[AWGConfig]:
        ...

    @abstractmethod
    def scope_capture(self, channel: int, sample_count: int = 8192, sample_rate: float | None = None) -> WaveformData:
        ...

    @abstractmethod
    def psu_set(self, channel: int, voltage: float) -> bool:
        ...

    @abstractmethod
    def psu_get(self, channel: int) -> float:
        ...

    @abstractmethod
    def psu_enable(self, channel: int) -> bool:
        ...

    @abstractmethod
    def psu_disable(self, channel: int) -> bool:
        ...

    @abstractmethod
    def logic_capture(
        self,
        channels: list[int] | None = None,
        sample_count: int = 8192,
        sample_rate: float | None = None,
        threshold: float = 1.5,
    ) -> LogicData:
        ...

    @abstractmethod
    def pattern_generate(self, config: PatternConfig) -> bool:
        ...

    @abstractmethod
    def pattern_stop(self, channel: int) -> bool:
        ...

    @abstractmethod
    def pattern_status(self) -> list[PatternConfig]:
        ...


class MockBackend(Backend):
    def __init__(self):
        self._connected = False
        self._awg_configs: dict[int, AWGConfig] = {
            1: AWGConfig(channel=1),
            2: AWGConfig(channel=2),
        }
        self._psu_voltages: dict[int, float] = {0: 0.0, 1: 0.0}
        self._psu_enabled: dict[int, bool] = {0: False, 1: False}
        self._pattern_configs: dict[int, PatternConfig] = {}

    def list_devices(self) -> list[dict[str, Any]]:
        return [
            {"serial": "MOCK-0001", "name": "ADALM2000 (Mock)", "uri": "mock"},
        ]

    def connect(self) -> DeviceInfo:
        self._connected = True
        return DeviceInfo(
            connected=True, serial="MOCK-0001",
            name="ADALM2000 (Mock)", mock=True,
        )

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def status(self) -> DeviceInfo:
        return DeviceInfo(
            connected=self._connected, serial="MOCK-0001",
            name="ADALM2000 (Mock)", mock=True,
        )

    def awg_configure(self, config: AWGConfig) -> bool:
        self._awg_configs[config.channel] = config
        return True

    def awg_start(self, channel: int) -> bool:
        if channel not in self._awg_configs:
            return False
        self._awg_configs[channel].enabled = True
        return True

    def awg_stop(self, channel: int) -> bool:
        if channel not in self._awg_configs:
            return False
        self._awg_configs[channel].enabled = False
        return True

    def awg_status(self) -> list[AWGConfig]:
        return list(self._awg_configs.values())

    def scope_capture(self, channel: int, sample_count: int = 8192, sample_rate: float | None = None) -> WaveformData:
        sr = sample_rate or 1e6
        t = np.arange(sample_count) / sr
        cfg = self._awg_configs.get(channel, AWGConfig(channel=channel))
        if cfg.waveform == "sine":
            sig = cfg.amplitude * np.sin(2 * math.pi * cfg.frequency * t + cfg.phase) + cfg.offset
        elif cfg.waveform == "square":
            sig = cfg.amplitude * np.sign(np.sin(2 * math.pi * cfg.frequency * t + cfg.phase)) + cfg.offset
        elif cfg.waveform == "triangle":
            sig = cfg.amplitude * (2 * np.abs(2 * (cfg.frequency * t + cfg.phase / (2 * math.pi)) % 2 - 1) - 1) + cfg.offset
        elif cfg.waveform == "sawtooth":
            sig = cfg.amplitude * (2 * ((cfg.frequency * t + cfg.phase / (2 * math.pi)) % 1) - 1) + cfg.offset
        elif cfg.waveform == "dc":
            sig = np.full(sample_count, cfg.offset)
        else:
            sig = cfg.amplitude * np.sin(2 * math.pi * 1000 * t) + 0.1 * np.random.randn(sample_count)
        vmin = float(np.min(sig))
        vmax = float(np.max(sig))
        return WaveformData(
            channel=channel,
            samples=sig.tolist(),
            sample_rate=sr,
            time_span=sample_count / sr,
            vpp=vmax - vmin,
            vmin=vmin,
            vmax=vmax,
            frequency=cfg.frequency if cfg.waveform != "dc" else None,
        )

    def psu_set(self, channel: int, voltage: float) -> bool:
        if channel not in (0, 1):
            return False
        self._psu_voltages[channel] = max(min(voltage, 5.0), -5.0)
        return True

    def psu_get(self, channel: int) -> float:
        return self._psu_voltages.get(channel, 0.0)

    def psu_enable(self, channel: int) -> bool:
        self._psu_enabled[channel] = True
        return True

    def psu_disable(self, channel: int) -> bool:
        self._psu_enabled[channel] = False
        return True

    def _generate_uart_message(self, text: str, baud: int, sr: float, n: int) -> list[int]:
        samples_per_bit = int(sr / baud)
        bits = []
        for char in text.encode("ascii"):
            frame = [0]  # start bit
            for i in range(8):
                frame.append((char >> i) & 1)
            frame.append(1)  # stop bit
            for b in frame:
                bits.extend([b] * samples_per_bit)
        bits.extend([1] * (n - len(bits)))
        return bits[:n]

    def logic_capture(
        self,
        channels: list[int] | None = None,
        sample_count: int = 8192,
        sample_rate: float | None = None,
        threshold: float = 1.5,
    ) -> LogicData:
        sr = sample_rate or 100e6
        n = sample_count
        chs = channels or [0, 1, 2, 3]
        samples = [0] * n

        for ch in chs:
            ch_mask = 1 << ch
            if ch == 0:
                bits = self._generate_uart_message("Hello", 115200, sr, n)
                for i, b in enumerate(bits):
                    if b:
                        samples[i] |= ch_mask
            elif ch == 1:
                duty = 0.6
                period = max(int(sr / 100000), 2)
                high = int(period * duty)
                for i in range(n):
                    if (i % period) < high:
                        samples[i] |= ch_mask
            elif ch == 2:
                half = int(sr / 200_000)
                for i in range(n):
                    if (i // half) % 2 == 1:
                        samples[i] |= ch_mask
            elif ch == 3:
                for i in range(n):
                    if i < n // 2:
                        samples[i] |= ch_mask

        return LogicData(
            channels=chs,
            samples=samples,
            sample_rate=sr,
            time_span=n / sr,
            bits_per_sample=16,
        )

    def _generate_pattern_samples(self, cfg: PatternConfig) -> list[int]:
        sr = cfg.sample_rate
        if cfg.data:
            return cfg.data[:]
        if cfg.waveform == "constant":
            return [0xFF] * 1024
        period = max(int(sr / max(cfg.frequency, 1)), 2)
        high = int(period * cfg.duty_cycle / 100.0)
        n = period * 10
        samples = []
        for i in range(n):
            val = 0xFF if (i % period) < high else 0x00
            samples.append(val)
        return samples

    def pattern_generate(self, config: PatternConfig) -> bool:
        self._pattern_configs[config.channel] = config
        return True

    def pattern_stop(self, channel: int) -> bool:
        cfg = self._pattern_configs.get(channel)
        if cfg:
            cfg.enabled = False
        return True

    def pattern_status(self) -> list[PatternConfig]:
        return list(self._pattern_configs.values())


def create_backend(mock: bool = False) -> Backend:
    if mock:
        return MockBackend()
    try:
        from adalm2000_mcp.iio_backend import IioBackend
        bk = IioBackend()
        devs = bk.list_devices()
        if devs:
            return bk
        return MockBackend()
    except Exception:
        return MockBackend()
