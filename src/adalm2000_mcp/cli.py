import importlib.metadata

import click
from adalm2000_mcp.server import run_server

try:
    _version = importlib.metadata.version("adalm2000-mcp")
except importlib.metadata.PackageNotFoundError:
    _version = "0.0.0"


@click.group()
@click.version_option(version=_version, prog_name="adalm2000-mcp")
def main():
    pass


@main.command()
@click.option("--mock", is_flag=True, help="Force mock mode (no hardware)")
@click.option("--http", is_flag=True, help="HTTP mode instead of STDIO")
@click.option("--port", default=10892, help="HTTP port")
@click.option("--transport", default=None, help="Transport (stdio, http)")
def serve(mock: bool, http: bool, port: int, transport: str | None):
    run_server(mock=mock, http=http, port=port, transport=transport)


@main.command()
def version():
    click.echo(f"adalm2000-mcp {_version}")


@main.command()
def check():
    from adalm2000_mcp.iio_backend import IioBackend
    try:
        devs = IioBackend().list_devices()
        if devs:
            click.echo("ADALM2000 detected!")
            for d in devs:
                click.echo(f"  {d['name']} ({d['uri']})")
        else:
            click.echo("No ADALM2000 detected. Use --mock for simulation.")
    except Exception as e:
        click.echo(f"Error: {e}")


if __name__ == "__main__":
    main()
