from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm

from clipdrop import __version__
from clipdrop import clipboard, detect, files, images

console = Console()


def version_callback(value: bool):
    """Handle --version flag."""
    if value:
        console.print(f"[cyan]clipdrop version {__version__}[/cyan]")
        raise typer.Exit()


def main(
    filename: Optional[str] = typer.Argument(
        None,
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
    text_mode: bool = typer.Option(
        False,
        "--text",
        "-t",
        help="Force text mode when both image and text exist in clipboard"
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
    Save clipboard content to files with smart format detection.

    Examples:
        clipdrop notes       # Saves to notes.txt
        clipdrop data.json   # Saves as JSON if valid
        clipdrop image.png   # Saves image from clipboard
    """
    # If no filename is provided, show error
    if filename is None:
        console.print("[red]Error: Missing argument 'FILENAME'.[/red]")
        console.print("\n[yellow]Usage: clipdrop [OPTIONS] FILENAME[/yellow]")
        console.print("\nTry 'clipdrop --help' for more information.")
        raise typer.Exit(1)

    try:
        # Determine content type in clipboard
        content_type = clipboard.get_content_type()

        if content_type == 'none':
            console.print("[red]📋 Clipboard is empty.[/red] Copy some content and try again.")
            raise typer.Exit(1)

        # Handle content priority
        use_image = False
        content = None
        image = None

        if content_type == 'both':
            # Both image and text exist
            if text_mode:
                console.print("[cyan]ℹ️  Both image and text found. Using text mode.[/cyan]")
                content = clipboard.get_text()
            else:
                console.print("[cyan]ℹ️  Both image and text found. Using image (use --text for text).[/cyan]")
                use_image = True
                image = clipboard.get_image()
        elif content_type == 'image':
            use_image = True
            image = clipboard.get_image()
            if image is None:
                console.print("[red]❌ Could not read image from clipboard.[/red]")
                raise typer.Exit(1)
        else:  # text only
            content = clipboard.get_text()
            if content is None:
                console.print("[red]❌ Could not read clipboard content.[/red]")
                raise typer.Exit(1)

        # Validate and sanitize filename
        if not files.validate_filename(filename):
            filename = files.sanitize_filename(filename)
            console.print(f"[yellow]⚠️  Invalid characters in filename. Using: {filename}[/yellow]")

        if use_image:
            # Handle image save
            # Add extension if not present
            final_filename = images.add_image_extension(filename, image)
            if final_filename != filename:
                console.print(f"[cyan]📷 Auto-detected image format. Saving as: {final_filename}[/cyan]")

            # Create Path object
            file_path = Path(final_filename)

            # Show preview if requested
            if preview:
                info = clipboard.get_image_info()
                if info:
                    console.print(Panel(
                        f"[cyan]Image Preview[/cyan]\n"
                        f"Dimensions: {info['width']}x{info['height']} pixels\n"
                        f"Mode: {info['mode']}\n"
                        f"Has Transparency: {'Yes' if info['has_transparency'] else 'No'}",
                        title=f"Preview of {final_filename}",
                        expand=False
                    ))

                    # Confirm save after preview
                    if not Confirm.ask("[cyan]Save this image?[/cyan]", default=True):
                        console.print("[yellow]Operation cancelled.[/yellow]")
                        raise typer.Exit()

            # Save the image
            save_info = images.write_image(file_path, image, optimize=True, force=force)

            # Success message
            console.print(
                f"[green]✅ Saved image ({save_info['dimensions']}, "
                f"{save_info['file_size_human']}) to {file_path}[/green]"
            )

        else:
            # Handle text save (existing logic)
            # Add extension if not present
            final_filename = detect.add_extension(filename, content)
            if final_filename != filename:
                console.print(f"[cyan]📝 Auto-detected format. Saving as: {final_filename}[/cyan]")

            # Create Path object
            file_path = Path(final_filename)

            # Show preview if requested
            if preview:
                preview_content = clipboard.get_content_preview(200)
                if preview_content:
                    # Determine syntax highlighting based on extension
                    lexer_map = {
                        '.json': 'json',
                        '.md': 'markdown',
                        '.py': 'python',
                        '.js': 'javascript',
                        '.html': 'html',
                        '.css': 'css',
                        '.yaml': 'yaml',
                        '.yml': 'yaml',
                    }
                    lexer = lexer_map.get(file_path.suffix.lower(), 'text')

                    # Show syntax-highlighted preview
                    syntax = Syntax(
                        preview_content,
                        lexer,
                        theme="monokai",
                        line_numbers=True,
                        word_wrap=True
                    )
                    console.print(Panel(syntax, title=f"Preview of {final_filename}", expand=False))

                    # Confirm save after preview
                    if not Confirm.ask("[cyan]Save this content?[/cyan]", default=True):
                        console.print("[yellow]Operation cancelled.[/yellow]")
                        raise typer.Exit()

            # Check for large content warning
            content_size = len(content.encode('utf-8'))
            if content_size > 10 * 1024 * 1024:  # 10MB
                size_str = files.get_file_size(content)
                if not force:
                    if not Confirm.ask(f"[yellow]⚠️  Large clipboard content ({size_str}). Continue?[/yellow]"):
                        console.print("[yellow]Operation cancelled.[/yellow]")
                        raise typer.Exit()

            # Write the file
            files.write_text(file_path, content, force=force)

            # Success message
            size_str = files.get_file_size(content)
            console.print(f"[green]✅ Saved {size_str} to {file_path}[/green]")

    except typer.Abort:
        # User cancelled operation
        raise typer.Exit()
    except PermissionError as e:
        console.print(f"[red]❌ Permission denied:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1)


# Create the Typer app
app = typer.Typer(
    name="clipdrop",
    help="Save clipboard content to files with smart format detection",
    add_completion=False,
)

# Register main function as the only command
app.command()(main)

if __name__ == "__main__":
    app()