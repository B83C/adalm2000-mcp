# adalm2000-mcp

MCP server for ADALM2000 (M2k) — AWG, scope, and PSU control via FastMCP 3.4.

## Tools

| Tool | Operations |
|------|-----------|
| `adalm_device` | `list`, `connect`, `disconnect`, `status`, `check` |
| `adalm_awg` | `configure`, `start`, `stop`, `status` |
| `adalm_scope` | `capture`, `fft`, `measure` |
| `adalm_psu` | `set`, `get`, `enable`, `disable`, `status` |

## Usage

```bash
uvx adalm2000-mcp serve
```

### opencode config

```json
{
  "mcp": {
    "adalm2000-mcp": {
      "type": "local",
      "command": ["uvx", "adalm2000-mcp", "serve"]
    }
  }
}
```

### Generate a signal

```json
// Connect W1 to 1+ with a wire, then:
adalm_awg(operation="configure", channel=1, waveform="sine", frequency=1000, amplitude=1.0)
adalm_awg(operation="start", channel=1)
adalm_scope(operation="capture", channel=1, sample_count=4096)
```

## Backends

- **IIO backend** — real hardware via `libiio` (`iio_readdev`/`iio_writedev`)
- **Mock backend** — no hardware needed, generates synthetic waveforms

`ADALM_MCP_MOCK=force` to force mock mode.

## Wiring

| AWG output | Scope input |
|------------|-------------|
| W1 (pin 1) | 1+ (pin 1) |
| W2 (pin 2) | 2+ (pin 2) |
| GND        | GND         |

## Publish

```bash
git tag v0.2.0
git push --tags
```

GitHub Actions publishes to PyPI automatically.
