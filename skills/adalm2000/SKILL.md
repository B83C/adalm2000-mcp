---
name: adalm2000
description: |
  Control ADALM2000 (M2k) USB test instrument — AWG, oscilloscope,
  power supply, 16-channel logic analyzer with UART/SPI/I2C/PWM decoding.
  Trigger on: "adalm2000", "m2k", "adalm", "awg", "logic analyzer",
  "uart decode", "spi decode", "i2c decode", "pwm measure",
  "signal generator", "oscilloscope", "power supply", "bench test".
---

# ADALM2000

Control the Analog Devices ADALM2000 (M2k) USB lab instrument. Two interfaces:
**MCP tools** (agent use) and **CLI** (shell/script use).

Requires: `uvx adalm2000-mcp serve` running as an MCP server (configured in
opencode.json as `"adalm2000-mcp"`).

## Tools

### `adalm_device`
Operations: `list` `connect` `disconnect` `status` `check`
CLI: `adalm2000-mcp device <command>`

### `adalm_awg` — Signal Generator
```
adalm_awg(operation="configure", channel=1, waveform="sine", frequency=1000, amplitude=1.0, offset=0.0)
adalm_awg(operation="start", channel=1)
adalm_awg(operation="stop", channel=1)
adalm_awg(operation="status")
```
Waveforms: `sine` `square` `triangle` `sawtooth` `dc`
**Always `configure` then `start`.** Call `stop` when done.
CLI: `adalm2000-mcp awg <configure|start|stop> [options]`

### `adalm_scope` — Oscilloscope
```
adalm_scope(operation="capture", channel=1, sample_count=8192, sample_rate=None)
adalm_scope(operation="measure", channel=1)
adalm_scope(operation="fft", channel=1)
```
Returns Vpp, Vmin, Vmax, frequency, samples (capture) / Vrms (measure) / peak freq (fft).
CLI: `adalm2000-mcp scope <capture|measure|fft> [options]`

### `adalm_psu` — Power Supply
```
adalm_psu(operation="set", channel=0, voltage=3.3)
adalm_psu(operation="get", channel=0)
adalm_psu(operation="enable", channel=0)
adalm_psu(operation="disable", channel=0)
adalm_psu(operation="status")
```
Channel 0 = V+, 1 = V-. Range -5V to +5V.
CLI: `adalm2000-mcp psu <set|get|enable|disable> [options]`

### `adalm_logic` — Logic Analyzer & Protocol Decode
```
adalm_logic(operation="capture", channels="0,1,2", sample_count=100000)
adalm_logic(operation="decode_uart", channel=0, baud_rate=0, data_bits=8, parity="none", stop_bits=1.0)
adalm_logic(operation="decode_spi", sclk_channel=1, mosi_channel=0, miso_channel=None, cs_channel=3, cpol=0, cpha=0)
adalm_logic(operation="decode_i2c", scl_channel=1, sda_channel=0, address_bits=7)
adalm_logic(operation="decode_pwm", channel=1)
```
- UART: auto-baud when `baud_rate=0`. Idle=high, LSB-first data.
- SPI: CS active-low. Data sampled on CPOL/CPHA-defined clock edge.
- I2C: START=SDA↓ while SCL↑. STOP=SDA↑ while SCL↑.
- PWM: measures frequency + duty cycle.
CLI: `adalm2000-mcp logic <capture|decode-uart|decode-spi|decode-i2c|decode-pwm> [options]`

## Common Workflows

**Generate sine & capture:**
```
adalm_awg(operation="configure", channel=1, waveform="sine", frequency=1000, amplitude=1)
adalm_awg(operation="start", channel=1)
adalm_scope(operation="capture", channel=1)
adalm_awg(operation="stop", channel=1)
```

**Decode UART on DIO0:**
```
adalm_logic(operation="decode_uart", channel=0, baud_rate=115200)
```

**Measure PWM on DIO1:**
```
adalm_logic(operation="decode_pwm", channel=1)
```

**Power a breadboard at 3.3V:**
```
adalm_psu(operation="set", channel=0, voltage=3.3)
adalm_psu(operation="enable", channel=0)
```

## Mock Mode

Test without hardware:
```bash
ADALM_MCP_MOCK=force uvx adalm2000-mcp serve
# or CLI:
adalm2000-mcp --mock logic decode-uart
```

Mock generates: UART "Hello" on ch0, 100kHz 60% PWM on ch1, 200kHz clock on ch2.
