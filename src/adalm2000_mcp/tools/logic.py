from __future__ import annotations

import numpy as np

from adalm2000_mcp.backend import Backend, LogicData


def _extract_channel(samples: list[int], channel: int) -> list[int]:
    mask = 1 << channel
    return [1 if (s & mask) else 0 for s in samples]


def _find_edges(bits: list[int]) -> list[tuple[int, int]]:
    edges = []
    for i in range(1, len(bits)):
        if bits[i] != bits[i - 1]:
            edges.append((i, bits[i]))
    return edges


def decode_uart(data: LogicData, channel: int = 0, baud_rate: int = 0,
                data_bits: int = 8, parity: str = "none", stop_bits: float = 1.0) -> dict:
    bits = _extract_channel(data.samples, channel)
    sr = data.sample_rate
    if baud_rate <= 0:
        edges = _find_edges(bits)
        if len(edges) < 2:
            return {"error": "No edges found, cannot auto-detect baud"}
        min_gap = min(edges[i + 1][0] - edges[i][0] for i in range(len(edges) - 1))
        baud_rate = int(sr / max(min_gap, 1))
        baud_rate = min(baud_rate, 3000000)

    spb = int(sr / baud_rate)
    decoded = []
    i = 0
    n = len(bits)
    while i < n - spb:
        if bits[i] == 0:
            start = i
            frame_start = start + spb
            byte_val = 0
            for bit_idx in range(data_bits):
                sample_pos = frame_start + bit_idx * spb + spb // 2
                if sample_pos < n and bits[sample_pos]:
                    byte_val |= 1 << bit_idx
            parity_ok = None
            if parity != "none":
                parity_pos = frame_start + data_bits * spb + spb // 2
                parity_bit = bits[parity_pos] if parity_pos < n else 0
                ones = bin(byte_val).count("1")
                if parity == "even":
                    parity_ok = (ones + parity_bit) % 2 == 0
                else:
                    parity_ok = (ones + parity_bit) % 2 == 1
            stop_pos = frame_start + (data_bits + (1 if parity != "none" else 0)) * spb + spb // 2
            stop_ok = bits[stop_pos] == 1 if stop_pos < n else False
            ch = chr(byte_val) if 32 <= byte_val < 127 else None
            decoded.append({
                "byte": byte_val,
                "char": ch,
                "hex": f"0x{byte_val:02x}",
                "parity_ok": parity_ok,
                "stop_ok": stop_ok,
            })
            advance = frame_start + (data_bits + (1 if parity != "none" else 0) + int(stop_bits)) * spb
            i = advance
        else:
            i += 1

    return {
        "protocol": "UART",
        "baud_rate": baud_rate,
        "data_bits": data_bits,
        "parity": parity,
        "stop_bits": stop_bits,
        "frames": decoded,
        "frame_count": len(decoded),
        "text": "".join(f["char"] for f in decoded if f["char"] is not None),
    }


def decode_spi(data: LogicData, sclk_ch: int = 1, mosi_ch: int = 0,
               miso_ch: int | None = None, cs_ch: int | None = None,
               cpol: int = 0, cpha: int = 0, bit_order: str = "msb") -> dict:
    sclk = _extract_channel(data.samples, sclk_ch)
    mosi = _extract_channel(data.samples, mosi_ch)
    miso = _extract_channel(data.samples, miso_ch) if miso_ch is not None else None
    cs = _extract_channel(data.samples, cs_ch) if cs_ch is not None else None

    if cs is not None:
        cs_active = [i for i in range(1, len(cs)) if cs[i - 1] == 1 and cs[i] == 0]
        cs_inactive = [i for i in range(1, len(cs)) if cs[i - 1] == 0 and cs[i] == 1]
        if not cs_active:
            return {"protocol": "SPI", "error": "No CS assertion detected"}
        transactions = []
        for start_idx in cs_active:
            end_idx = next((x for x in cs_inactive if x > start_idx), len(cs) - 1)
            mosi_bits, miso_bits = [], []
            for i in range(start_idx, min(end_idx + 1, len(sclk) - 1)):
                if cpha == 0:
                    edge = (sclk[i] == cpol and sclk[i + 1] != cpol)
                else:
                    edge = (sclk[i] != cpol and sclk[i + 1] == cpol)
                if edge:
                    mosi_bits.append(mosi[i])
                    if miso is not None:
                        miso_bits.append(miso[i])
            mosi_val = 0
            for b in (mosi_bits if bit_order == "msb" else reversed(mosi_bits)):
                mosi_val = (mosi_val << 1) | b
            miso_val = 0
            for b in (miso_bits if bit_order == "msb" else reversed(miso_bits)):
                miso_val = (miso_val << 1) | b
            transactions.append({
                "mosi_hex": f"0x{mosi_val:0{(len(mosi_bits) + 3) // 4}x}" if mosi_bits else None,
                "miso_hex": f"0x{miso_val:0{(len(miso_bits) + 3) // 4}x}" if miso_bits else None,
                "bits": len(mosi_bits) if mosi_bits else 0,
            })
        return {
            "protocol": "SPI", "cpol": cpol, "cpha": cpha,
            "bit_order": bit_order, "transactions": transactions,
            "transaction_count": len(transactions),
        }
    return {"protocol": "SPI", "error": "CS channel required for SPI decoding"}


def decode_i2c(data: LogicData, scl_ch: int = 1, sda_ch: int = 0,
               address_bits: int = 7) -> dict:
    scl = _extract_channel(data.samples, scl_ch)
    sda = _extract_channel(data.samples, sda_ch)
    n = len(scl)

    transactions = []
    i = 0
    while i < n - 10:
        if scl[i] == 1 and sda[i] == 1 and sda[i + 1] == 0:
            start_idx = i + 1
            addr_val = 0
            ack = True
            for bit_idx in range(address_bits + 1):
                for j in range(start_idx, n - 1):
                    if scl[j] == 0 and scl[j + 1] == 1:
                        if bit_idx < address_bits:
                            addr_val = (addr_val << 1) | sda[j + 1]
                        else:
                            rw = sda[j + 1]
                        start_idx = j + 2
                        break
            for j in range(start_idx, n - 1):
                if scl[j] == 0 and scl[j + 1] == 1:
                    ack = (sda[j + 1] == 0)
                    start_idx = j + 2
                    break
            data_bytes = []
            while start_idx < n:
                for j in range(start_idx, n - 1):
                    if scl[j] == 1 and sda[j] == 0 and sda[j + 1] == 1:
                        return {
                            "protocol": "I2C",
                            "transactions": transactions,
                            "transaction_count": len(transactions),
                        }
                stop_found = False
                for j in range(start_idx, n - 1):
                    if scl[j] == 1 and sda[j] == 0 and sda[j + 1] == 1:
                        stop_found = True
                        start_idx = j + 2
                        break
                if stop_found:
                    break
                byte_val = 0
                byte_ack = True
                for bit_idx in range(9):
                    for j in range(start_idx, n - 1):
                        if scl[j] == 0 and scl[j + 1] == 1:
                            if bit_idx < 8:
                                byte_val = (byte_val << 1) | sda[j + 1]
                            else:
                                byte_ack = (sda[j + 1] == 0)
                            start_idx = j + 2
                            break
                data_bytes.append({"byte": byte_val, "ack": byte_ack, "char": chr(byte_val) if 32 <= byte_val < 127 else None})
                if not byte_ack:
                    break
            transactions.append({
                "address": addr_val,
                "address_hex": f"0x{addr_val:02x}",
                "read": bool(rw),
                "ack": ack,
                "data": data_bytes,
            })
        else:
            i += 1

    return {
        "protocol": "I2C",
        "address_bits": address_bits,
        "transactions": transactions,
        "transaction_count": len(transactions),
    }


def decode_pwm(data: LogicData, channel: int = 0) -> dict:
    bits = _extract_channel(data.samples, channel)
    sr = data.sample_rate
    edges = _find_edges(bits)
    if len(edges) < 2:
        return {"channel": channel, "error": "Not enough edges for PWM measurement"}
    periods = []
    duty_cycles = []
    for k in range(2, len(edges)):
        period_samples = abs(edges[k][0] - edges[k - 2][0])
        if period_samples > 0:
            seg_samples = edges[k - 1][0] - edges[k - 2][0]
            if edges[k - 1][1] == 0:
                high_samples = seg_samples
            else:
                high_samples = period_samples - seg_samples
            high_samples = max(0, min(high_samples, period_samples))
            periods.append(period_samples / sr)
            duty_cycles.append(high_samples / period_samples)
    if not periods:
        return {"channel": channel, "error": "Could not measure PWM"}
    avg_period = float(np.mean(periods))
    avg_freq = 1.0 / avg_period if avg_period > 0 else 0
    avg_duty = float(np.mean(duty_cycles)) * 100
    return {
        "channel": channel,
        "protocol": "PWM",
        "frequency_hz": round(avg_freq, 1),
        "period_s": round(avg_period, 9),
        "duty_cycle_pct": round(avg_duty, 1),
        "measurements": len(periods),
    }


def handle_logic(
    backend: Backend,
    operation: str,
    channel: int = 0,
    channels: str = "",
    sample_count: int = 100000,
    sample_rate: float | None = None,
    threshold: float = 1.5,
    baud_rate: int = 115200,
    data_bits: int = 8,
    parity: str = "none",
    stop_bits: float = 1.0,
    protocol: str = "",
    sclk_channel: int = 1,
    mosi_channel: int = 0,
    miso_channel: int | None = None,
    cs_channel: int | None = None,
    scl_channel: int = 1,
    sda_channel: int = 0,
    cpol: int = 0,
    cpha: int = 0,
    bit_order: str = "msb",
    address_bits: int = 7,
) -> dict:
    ops_capture = {"capture", "decode_uart", "decode_spi", "decode_i2c", "decode_pwm"}

    if operation not in ops_capture and operation != "status":
        return {"success": False, "error": f"Unknown operation: {operation}"}

    if operation == "status":
        return {
            "success": True,
            "digital_channels": 16,
            "max_sample_rate": 100e6,
        }

    parsed_channels = [int(c.strip()) for c in channels.split(",") if c.strip()] if channels else None
    if operation == "capture":
        chs = parsed_channels or [channel]
        data = backend.logic_capture(chs, sample_count, sample_rate, threshold)
        time_span = data.time_span
        transitions = []
        prev = 0
        for i, s in enumerate(data.samples):
            if s != prev:
                transitions.append({"index": i, "time_us": round(i / data.sample_rate * 1e6, 2), "value": s})
                prev = s
        return {
            "success": True,
            "channels": chs,
            "sample_rate": data.sample_rate,
            "time_span": time_span,
            "total_samples": len(data.samples),
            "transitions": transitions[:200],
            "transition_count": len(transitions),
        }

    elif operation == "decode_uart":
        chs = parsed_channels or [channel]
        data = backend.logic_capture(chs, sample_count, sample_rate, threshold)
        result = decode_uart(data, channel=chs[0], baud_rate=baud_rate,
                             data_bits=data_bits, parity=parity, stop_bits=stop_bits)
        return {"success": True, **result}

    elif operation == "decode_spi":
        chs = set(parsed_channels or [])
        chs.add(sclk_channel)
        chs.add(mosi_channel)
        if miso_channel is not None:
            chs.add(miso_channel)
        if cs_channel is not None:
            chs.add(cs_channel)
        data = backend.logic_capture(list(chs), sample_count, sample_rate, threshold)
        result = decode_spi(data, sclk_ch=sclk_channel, mosi_ch=mosi_channel,
                            miso_ch=miso_channel, cs_ch=cs_channel,
                            cpol=cpol, cpha=cpha, bit_order=bit_order)
        return {"success": True, **result}

    elif operation == "decode_i2c":
        chs = set(parsed_channels or [])
        chs.add(scl_channel)
        chs.add(sda_channel)
        data = backend.logic_capture(list(chs), sample_count, sample_rate, threshold)
        result = decode_i2c(data, scl_ch=scl_channel, sda_ch=sda_channel,
                            address_bits=address_bits)
        return {"success": True, **result}

    elif operation == "decode_pwm":
        chs = parsed_channels or [channel]
        data = backend.logic_capture(chs, sample_count, sample_rate, threshold)
        result = decode_pwm(data, channel=chs[0])
        return {"success": True, **result}

    return {"success": False, "error": f"Unknown operation: {operation}"}
