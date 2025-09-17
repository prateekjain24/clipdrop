import typer
from typing import Optional

from clipdrop import __version__

app = typer.Typer(
    name="clipdrop",
    help="Save clipboard content to files with smart format detection",
    add_completion=False,
)


def version_callback(value: bool):
    if value:
        print(f"clipdrop version {__version__}")
        raise typer.Exit()


@app.command()
def main(
    filename: str = typer.Argument(
        ...,
        help="Filename to save clipboard content to (with or without extension)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force overwrite if file exists"
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        "-p",
        help="Preview clipboard content before saving"
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit"
    ),
):
    """
    Save clipboard content to a file.

    Examples:
        clipdrop notes       # Saves to notes.txt
        clipdrop data.json   # Saves as JSON if valid
        clipdrop image.png   # Saves image from clipboard
    """
    # TODO: Implement clipboard reading and file saving logic
    typer.echo(f"Saving clipboard content to {filename}...")
    typer.echo("Feature not yet implemented.")


if __name__ == "__main__":
    app()