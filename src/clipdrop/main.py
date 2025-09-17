from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm

from clipdrop import __version__
from clipdrop import clipboard, detect, files, images
from clipdrop.error_helpers import display_error, show_success_message

console = Console()


def version_callback(value: bool):
    """Handle --version flag."""
    if value:
        console.print(f"[cyan]clipdrop version {__version__}[/cyan]")
        raise typer.Exit()


def main(
    filename: Optional[str] = typer.Argument(
        None,
        help="Target filename for clipboard content. Extension optional - ClipDrop auto-detects format (e.g., 'notes' → 'notes.txt', 'data' → 'data.json')"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation and overwrite existing files. Useful for scripts and automation"
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        "-p",
        help="Preview content before saving. Shows syntax-highlighted text or image dimensions with save confirmation"
    ),
    text_mode: bool = typer.Option(
        False,
        "--text",
        "-t",
        help="Prioritize text over images when both exist in clipboard. Useful when you want the text instead of a screenshot"
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

    ClipDrop automatically detects content types and suggests appropriate file extensions.
    It handles both text and images, with intelligent format detection for JSON, Markdown,
    CSV, and various image formats.

    [bold cyan]Quick Examples:[/bold cyan]

      [green]Text:[/green]
        clipdrop notes              # Auto-detects format → notes.txt
        clipdrop data               # JSON detected → data.json
        clipdrop readme             # Markdown detected → readme.md

      [green]Images:[/green]
        clipdrop screenshot         # Saves clipboard image → screenshot.png
        clipdrop photo.jpg          # Saves as JPEG with optimization

      [green]Mixed Content:[/green]
        clipdrop content            # Prioritizes image if both exist
        clipdrop content --text     # Forces text mode

    [bold cyan]Smart Features:[/bold cyan]

      • Auto-detects JSON, Markdown, CSV formats
      • Optimizes images (PNG/JPEG compression)
      • Handles mixed clipboard content intelligently
      • Protects against accidental overwrites
      • Shows preview before saving

    [bold cyan]Common Workflows:[/bold cyan]

      1. Copy code/text → clipdrop script.py
      2. Take screenshot → clipdrop screenshot.png
      3. Copy JSON API response → clipdrop response.json
      4. Copy markdown notes → clipdrop notes.md

    [dim]For more help, visit: https://github.com/prateekjain24/clipdrop[/dim]
    """
    # If no filename is provided, show error
    if filename is None:
        console.print("\n[red]📝 Please provide a filename[/red]")
        console.print("[yellow]Usage: clipdrop [OPTIONS] FILENAME[/yellow]")
        console.print("\n[dim]Examples:[/dim]")
        console.print("  clipdrop notes.txt    # Save text")
        console.print("  clipdrop image.png    # Save image")
        console.print("  clipdrop data.json    # Save JSON")
        console.print("\n[dim]Try 'clipdrop --help' for more options[/dim]")
        raise typer.Exit(1)

    try:
        # Determine content type in clipboard
        content_type = clipboard.get_content_type()

        if content_type == 'none':
            display_error('empty_clipboard')
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
            show_success_message(
                file_path,
                'image',
                save_info['file_size_human'],
                {
                    'dimensions': save_info['dimensions'],
                    'optimized': True,
                    'format_detected': save_info['format']
                }
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
            content_format = detect.detect_format(content)
            show_success_message(
                file_path,
                content_format if content_format != 'txt' else 'text',
                size_str,
                {'format_detected': content_format}
            )

    except typer.Abort:
        # User cancelled operation
        raise typer.Exit()
    except PermissionError as e:
        display_error('permission_denied', {'filename': filename})
        raise typer.Exit(1)
    except files.PathTraversalError:
        display_error('invalid_path', {'filename': filename})
        raise typer.Exit(1)
    except Exception as e:
        # Generic error with helpful message
        console.print(f"\n[red]❌ Unexpected error:[/red] {e}")
        console.print("\n[yellow]💡 Troubleshooting tips:[/yellow]")
        console.print("  1. Check if the file path is valid")
        console.print("  2. Ensure you have write permissions")
        console.print("  3. Try with --preview to see content first")
        console.print("\n[dim]Report issues: https://github.com/prateekjain24/clipdrop/issues[/dim]")
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