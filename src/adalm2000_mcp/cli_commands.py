from __future__ import annotations

import json
import os

import click

from adalm2000_mcp.backend import AWGConfig, Backend, create_backend


def _get_backend() -> Backend:
    try:
        ctx = click.get_current_context()
        mock = ctx.obj.get("mock", False)
    except (RuntimeError, AttributeError, KeyError):
        mock = os.environ.get("ADALM_MCP_MOCK", "auto") in ("true", "1", "force")
    return create_backend(mock=mock)


def _pp(data: dict) -> None:
    click.echo(json.dumps(data, indent=2, default=str))


@click.group()
def awg():
    pass


@awg.command()
@click.option("--channel", default=1, type=int, help="AWG channel (1 or 2)")
@click.option("--waveform", default="sine", help="Waveform: sine/square/triangle/sawtooth/dc")
@click.option("--frequency", default=1000.0, type=float, help="Frequency in Hz")
@click.option("--amplitude", default=1.0, type=float, help="Amplitude in V")
@click.option("--offset", default=0.0, type=float, help="DC offset in V")

def configure(channel: int, waveform: str, frequency: float, amplitude: float, offset: float):
    b = _get_backend()
    cfg = AWGConfig(channel=channel, waveform=waveform, frequency=frequency, amplitude=amplitude, offset=offset)
    ok = b.awg_configure(cfg)
    click.echo(f"Channel {channel} configured: {waveform} @ {frequency} Hz, {amplitude} Vpk" if ok else "Failed")


@awg.command()
@click.option("--channel", default=1, type=int, help="AWG channel (1 or 2)")

def start(channel: int):
    b = _get_backend()
    ok = b.awg_start(channel)
    click.echo(f"AWG channel {channel} started" if ok else "Failed")


@awg.command()
@click.option("--channel", default=1, type=int, help="AWG channel (1 or 2)")

def stop(channel: int):
    b = _get_backend()
    ok = b.awg_stop(channel)
    click.echo(f"AWG channel {channel} stopped" if ok else "Failed")


@awg.command()

def status():
    b = _get_backend()
    configs = b.awg_status()
    for c in configs:
        click.echo(f"  Ch{c.channel}: {c.waveform} @ {c.frequency} Hz, {c.amplitude} Vpk, enabled={c.enabled}")


@click.group()
def scope():
    pass


@scope.command()
@click.option("--channel", default=1, type=int, help="Scope channel (1 or 2)")
@click.option("--sample-count", default=8192, type=int)
@click.option("--sample-rate", default=None, type=float, help="Sample rate in Hz")

def capture(channel: int, sample_count: int, sample_rate: float | None):
    b = _get_backend()
    data = b.scope_capture(channel, sample_count, sample_rate)
    click.echo(f"Channel {channel}: Vpp={data.vpp:.4f}V, Vmin={data.vmin:.4f}V, Vmax={data.vmax:.4f}V")
    click.echo(f"  Sample rate: {data.sample_rate:.0f} Hz, Time span: {data.time_span*1e6:.2f} us")
    click.echo(f"  Samples: {len(data.samples)}")


@scope.command()
@click.option("--channel", default=1, type=int)
@click.option("--sample-count", default=8192, type=int)
@click.option("--sample-rate", default=None, type=float)

def measure(channel: int, sample_count: int, sample_rate: float | None):
    b = _get_backend()
    data = b.scope_capture(channel, sample_count, sample_rate)
    import numpy as np
    sig = np.array(data.samples)
    rms = float(np.sqrt(np.mean(sig ** 2)))
    click.echo(f"Channel {channel}: Vpp={data.vpp:.4f}V, Vrms={rms:.4f}V, Vmin={data.vmin:.4f}V, Vmax={data.vmax:.4f}V")
    if data.frequency:
        click.echo(f"  Frequency: {data.frequency:.1f} Hz")


@scope.command()
@click.option("--channel", default=1, type=int)
@click.option("--sample-count", default=8192, type=int)
@click.option("--sample-rate", default=None, type=float)

def fft(channel: int, sample_count: int, sample_rate: float | None):
    b = _get_backend()
    data = b.scope_capture(channel, sample_count, sample_rate)
    import numpy as np
    sig = np.array(data.samples)
    n = len(sig)
    window = np.hamming(n)
    fft_vals = np.fft.rfft(sig * window)
    fft_mag = np.abs(fft_vals) / n
    freqs = np.fft.rfftfreq(n, d=1.0 / data.sample_rate)
    peak_idx = int(np.argmax(fft_mag[1:])) + 1
    click.echo(f"Channel {channel}: peak at {freqs[peak_idx]:.1f} Hz (magnitude {fft_mag[peak_idx]:.4f})")
    for f, m in zip(freqs[:20], fft_mag[:20]):
        click.echo(f"  {f:.0f} Hz: {m:.4f}")


@click.group()
def psu():
    pass


@psu.command()
@click.option("--channel", default=0, type=int, help="PSU channel 0 (V+) or 1 (V-)")
@click.option("--voltage", default=0.0, type=float, help="Voltage (-5 to +5 V)")

def set(channel: int, voltage: float):
    b = _get_backend()
    ok = b.psu_set(channel, voltage)
    label = "V+" if channel == 0 else "V-"
    click.echo(f"PSU {label} set to {voltage}V" if ok else "Failed")


@psu.command()
@click.option("--channel", default=0, type=int, help="PSU channel 0 (V+) or 1 (V-)")

def get(channel: int):
    b = _get_backend()
    v = b.psu_get(channel)
    label = "V+" if channel == 0 else "V-"
    click.echo(f"PSU {label}: {v}V")


@psu.command()
@click.option("--channel", default=0, type=int)

def enable(channel: int):
    b = _get_backend()
    ok = b.psu_enable(channel)
    label = "V+" if channel == 0 else "V-"
    click.echo(f"PSU {label} enabled" if ok else "Failed")


@psu.command()
@click.option("--channel", default=0, type=int)

def disable(channel: int):
    b = _get_backend()
    ok = b.psu_disable(channel)
    label = "V+" if channel == 0 else "V-"
    click.echo(f"PSU {label} disabled" if ok else "Failed")


@psu.command()

def status():
    b = _get_backend()
    for ch in (0, 1):
        label = "V+" if ch == 0 else "V-"
        v = b.psu_get(ch)
        click.echo(f"  {label}: {v}V")


@click.group()
def logic():
    pass


@logic.command()
@click.option("--channels", default="0", help="Comma-separated channel numbers")
@click.option("--sample-count", default=100000, type=int)
@click.option("--sample-rate", default=None, type=float)
@click.option("--threshold", default=1.5, type=float)

def capture(channels: str, sample_count: int, sample_rate: float | None, threshold: float):
    from adalm2000_mcp.tools.logic import handle_logic
    b = _get_backend()
    result = handle_logic(b, "capture", channels=channels, sample_count=sample_count, sample_rate=sample_rate, threshold=threshold)
    if result["success"]:
        click.echo(f"Channels: {result['channels']}, Transitions: {result['transition_count']}, Samples: {result['total_samples']}")
        for t in result.get("transitions", [])[:20]:
            click.echo(f"  @ {t['time_us']} us: 0x{t['value']:04x}")
    else:
        click.echo(f"Error: {result.get('error')}")


@logic.command()
@click.option("--channel", default=0, type=int)
@click.option("--baud-rate", default=0, type=int, help="0 = auto-detect")
@click.option("--data-bits", default=8, type=int)
@click.option("--parity", default="none", help="none/even/odd")
@click.option("--stop-bits", default=1.0, type=float)
@click.option("--sample-count", default=100000, type=int)

def decode_uart(channel: int, baud_rate: int, data_bits: int, parity: str, stop_bits: float, sample_count: int):
    from adalm2000_mcp.tools.logic import handle_logic
    b = _get_backend()
    result = handle_logic(b, "decode_uart", channel=channel, sample_count=sample_count, baud_rate=baud_rate, data_bits=data_bits, parity=parity, stop_bits=stop_bits)
    if result["success"]:
        click.echo(f"UART @ {result['baud_rate']} baud, {result['frame_count']} frames")
        click.echo(f"Text: \"{result.get('text', '')}\"")
        for f in result.get("frames", []):
            click.echo(f"  0x{f['byte']:02x} {'\'' + (f['char'] or '') + '\'' if f.get('char') else ''}")
    else:
        click.echo(f"Error: {result.get('error')}")


@logic.command()
@click.option("--sclk-channel", default=1, type=int)
@click.option("--mosi-channel", default=0, type=int)
@click.option("--miso-channel", default=None, type=int)
@click.option("--cs-channel", default=None, type=int)
@click.option("--cpol", default=0, type=int)
@click.option("--cpha", default=0, type=int)
@click.option("--bit-order", default="msb", help="msb or lsb")
@click.option("--sample-count", default=100000, type=int)

def decode_spi(sclk_channel: int, mosi_channel: int, miso_channel: int | None, cs_channel: int | None, cpol: int, cpha: int, bit_order: str, sample_count: int):
    from adalm2000_mcp.tools.logic import handle_logic
    b = _get_backend()
    result = handle_logic(b, "decode_spi", sclk_channel=sclk_channel, mosi_channel=mosi_channel, miso_channel=miso_channel, cs_channel=cs_channel, cpol=cpol, cpha=cpha, bit_order=bit_order, sample_count=sample_count)
    if result["success"]:
        click.echo(f"SPI: {result.get('transaction_count', 0)} transactions")
        for t in result.get("transactions", []):
            click.echo(f"  MOSI={t.get('mosi_hex', 'N/A')}, MISO={t.get('miso_hex', 'N/A')}, bits={t.get('bits', 0)}")
    else:
        click.echo(f"Error: {result.get('error')}")


@logic.command()
@click.option("--scl-channel", default=1, type=int)
@click.option("--sda-channel", default=0, type=int)
@click.option("--address-bits", default=7, type=int)
@click.option("--sample-count", default=100000, type=int)

def decode_i2c(scl_channel: int, sda_channel: int, address_bits: int, sample_count: int):
    from adalm2000_mcp.tools.logic import handle_logic
    b = _get_backend()
    result = handle_logic(b, "decode_i2c", scl_channel=scl_channel, sda_channel=sda_channel, address_bits=address_bits, sample_count=sample_count)
    if result["success"]:
        click.echo(f"I2C: {result.get('transaction_count', 0)} transactions")
        for t in result.get("transactions", []):
            click.echo(f"  Addr=0x{t['address']:02x} {'R' if t.get('read') else 'W'} ack={t.get('ack')}")
            for d in t.get("data", []):
                click.echo(f"    0x{d['byte']:02x} {'\'' + (d.get('char') or '') + '\'' if d.get('char') else ''} ack={d.get('ack')}")
    else:
        click.echo(f"Error: {result.get('error')}")


@logic.command()
@click.option("--channel", default=0, type=int)
@click.option("--sample-count", default=100000, type=int)

def decode_pwm(channel: int, sample_count: int):
    from adalm2000_mcp.tools.logic import handle_logic
    b = _get_backend()
    result = handle_logic(b, "decode_pwm", channel=channel, sample_count=sample_count)
    if result["success"]:
        click.echo(f"PWM ch{channel}: {result.get('frequency_hz', '?')} Hz @ {result.get('duty_cycle_pct', '?')}%")
    else:
        click.echo(f"Error: {result.get('error')}")


@logic.command()

def status():
    from adalm2000_mcp.tools.logic import handle_logic
    b = _get_backend()
    result = handle_logic(b, "status")
    click.echo(f"Digital channels: {result.get('digital_channels', 16)}, Max rate: {result.get('max_sample_rate', 100e6):.0f} Hz")


@click.group()
def device():
    pass


@device.command()

def list():
    b = _get_backend()
    for d in b.list_devices():
        click.echo(f"  {d['name']} ({d['uri']})")


@device.command()

def status():
    b = _get_backend()
    info = b.status()
    click.echo(f"Connected: {info.connected}, Serial: {info.serial}, Name: {info.name}")
    if info.mock:
        click.echo("  (mock mode)")


@device.command()

def connect():
    b = _get_backend()
    info = b.connect()
    click.echo(f"Connected to {info.name} (serial: {info.serial})" if info.connected else "Failed to connect")


@device.command()

def disconnect():
    b = _get_backend()
    ok = b.disconnect()
    click.echo("Disconnected" if ok else "Failed")
