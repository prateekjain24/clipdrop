from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm

from clipdrop import __version__
from clipdrop import clipboard, detect, files, images, pdf
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
    educational: bool = typer.Option(
        True,
        "--educational/--no-educational",
        help="Enable educational content optimizations for better formatting in PDFs (justified text, callout boxes, enhanced spacing)"
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
        clipdrop document           # Mixed text+image → document.pdf
        clipdrop content --text     # Forces text mode
        clipdrop report.pdf         # Explicitly create PDF

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

        # Handle HTML mixed content (from web pages)
        if content_type == 'html_mixed':
            from clipdrop import html_parser
            # Try to get ordered chunks first
            html_content = html_parser.get_html_from_clipboard()
            if html_content:
                # Try enhanced parsing first for better structure preservation
                try:
                    enhanced_chunks = html_parser.parse_html_content_enhanced(html_content)
                    use_enhanced = len(enhanced_chunks) > 0
                except Exception:
                    # Fall back to standard parsing
                    enhanced_chunks = None
                    use_enhanced = False

                if use_enhanced and enhanced_chunks:
                    # Use enhanced PDF generation
                    file_path = Path(filename)

                    # Add .pdf extension if not present
                    if not file_path.suffix:
                        final_filename = f"{filename}.pdf"
                        console.print(f"[cyan]📄 HTML with enhanced structure detected. Creating PDF: {final_filename}[/cyan]")
                    elif file_path.suffix.lower() != '.pdf':
                        final_filename = f"{file_path.stem}.pdf"
                        console.print(f"[cyan]📄 HTML with enhanced structure detected. Creating PDF: {final_filename}[/cyan]")
                    else:
                        final_filename = filename
                        console.print("[cyan]📄 Creating enhanced PDF from HTML content...[/cyan]")

                    file_path = Path(final_filename)

                    # Count different content types for preview
                    content_counts = {}
                    total_text_len = 0
                    for chunk_type, content, metadata in enhanced_chunks:
                        content_counts[chunk_type] = content_counts.get(chunk_type, 0) + 1
                        if chunk_type in ['text', 'paragraph', 'heading']:
                            total_text_len += len(str(content))

                    # Show preview if requested
                    if preview:
                        preview_lines = ["[cyan]HTML Content (Enhanced):[/cyan]"]
                        preview_lines.append(f"Text: {total_text_len} characters")
                        for content_type, count in content_counts.items():
                            preview_lines.append(f"{content_type.title()}: {count} element(s)")

                        console.print(Panel(
                            "\n".join(preview_lines),
                            title=f"Preview: {final_filename}",
                            expand=False
                        ))
                        if not Confirm.ask("[cyan]Create this enhanced PDF?[/cyan]", default=True):
                            console.print("[yellow]Operation cancelled.[/yellow]")
                            raise typer.Exit()

                    # Create enhanced PDF
                    pdf.create_pdf_from_enhanced_html(
                        enhanced_chunks, file_path, educational_mode=educational
                    )

                    # Success message
                    file_size = file_path.stat().st_size
                    size_str = files.get_file_size_human(file_size)
                    console.print(f"[green]✅ Created enhanced PDF ({total_text_len} chars, {len(content_counts)} content types, {size_str}) at {file_path}[/green]")
                    raise typer.Exit()

                else:
                    # Fall back to standard ordered parsing
                    ordered_chunks = html_parser.parse_html_content_ordered(html_content)

                    if ordered_chunks:
                        file_path = Path(filename)

                        # Add .pdf extension if not present
                        if not file_path.suffix:
                            final_filename = f"{filename}.pdf"
                            console.print(f"[cyan]📄 HTML with images detected. Creating PDF: {final_filename}[/cyan]")
                        elif file_path.suffix.lower() != '.pdf':
                            final_filename = f"{file_path.stem}.pdf"
                            console.print(f"[cyan]📄 HTML with images detected. Creating PDF: {final_filename}[/cyan]")
                        else:
                            final_filename = filename
                            console.print("[cyan]📄 Creating PDF from HTML content with images...[/cyan]")

                        file_path = Path(final_filename)

                        # Count text and image chunks for preview
                        text_chunks = sum(1 for t, _ in ordered_chunks if t == 'text')
                        image_chunks = sum(1 for t, _ in ordered_chunks if t == 'image')
                        total_text_len = sum(len(c) for t, c in ordered_chunks if t == 'text' and isinstance(c, str))

                        # Show preview if requested
                        if preview:
                            console.print(Panel(
                                f"[cyan]HTML Content:[/cyan]\n"
                                f"Text: {total_text_len} characters in {text_chunks} sections\n"
                                f"Images: {image_chunks} embedded images",
                                title=f"Preview: {final_filename}",
                                expand=False
                            ))
                            if not Confirm.ask("[cyan]Create this PDF?[/cyan]", default=True):
                                console.print("[yellow]Operation cancelled.[/yellow]")
                                raise typer.Exit()

                        # Create PDF from ordered HTML content
                        pdf.create_pdf_from_html_ordered_content(
                            ordered_chunks, file_path
                        )

                        # Success message
                        file_size = file_path.stat().st_size
                        size_str = files.get_file_size_human(file_size)
                        console.print(f"[green]✅ Created PDF from HTML ({total_text_len} chars, {image_chunks} images, {size_str}) at {file_path}[/green]")
                        raise typer.Exit()

        # Get both text and image content (may be None)
        content = clipboard.get_text()
        image = clipboard.get_image()

        # Check if user explicitly wants PDF
        file_path = Path(filename)
        wants_pdf = file_path.suffix.lower() == '.pdf'

        # Determine what to save based on content and user preference
        use_pdf = False
        use_image = False

        if wants_pdf:
            # User explicitly requested PDF
            use_pdf = True
            console.print("[cyan]📄 Creating PDF from clipboard content...[/cyan]")
        elif content_type == 'both':
            # Both image and text exist
            if text_mode:
                console.print("[cyan]ℹ️  Both image and text found. Using text mode.[/cyan]")
                image = None  # Ignore image in text mode
            elif not file_path.suffix:
                # No extension provided, mixed content -> suggest PDF
                use_pdf = True
                console.print("[cyan]📄 Mixed content detected (text + image). Creating PDF to preserve both.[/cyan]")
            else:
                # Has extension, follow user's choice
                if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
                    use_image = True
                    content = None  # Use image only
                    console.print("[cyan]ℹ️  Both found. Using image (use --text for text only).[/cyan]")
                else:
                    image = None  # Use text only
                    console.print("[cyan]ℹ️  Both found. Using text (specify .pdf to include both).[/cyan]")
        elif content_type == 'image':
            use_image = True
            if image is None:
                console.print("[red]❌ Could not read image from clipboard.[/red]")
                raise typer.Exit(1)
        elif content_type == 'text':
            if content is None:
                console.print("[red]❌ Could not read clipboard content.[/red]")
                raise typer.Exit(1)

        # Validate and sanitize filename
        if not files.validate_filename(filename):
            filename = files.sanitize_filename(filename)
            console.print(f"[yellow]⚠️  Invalid characters in filename. Using: {filename}[/yellow]")

        if use_pdf:
            # Handle PDF creation
            # Add .pdf extension if not present
            if not file_path.suffix:
                final_filename = f"{filename}.pdf"
            else:
                final_filename = filename

            if final_filename != filename:
                console.print(f"[cyan]📄 Saving as PDF: {final_filename}[/cyan]")

            file_path = Path(final_filename)

            # Show preview if requested
            if preview:
                preview_parts = []
                if content:
                    preview_parts.append(f"[cyan]Text:[/cyan] {len(content)} characters")
                    preview_text = content[:100] + "..." if len(content) > 100 else content
                    preview_parts.append(f"[dim]{preview_text}[/dim]")
                if image:
                    info = clipboard.get_image_info()
                    if info:
                        preview_parts.append(f"\n[cyan]Image:[/cyan] {info['width']}x{info['height']} pixels, {info['mode']} mode")

                console.print(Panel(
                    "\n".join(preview_parts),
                    title=f"PDF Preview: {final_filename}",
                    expand=False
                ))

                # Confirm save after preview
                if not Confirm.ask("[cyan]Create this PDF?[/cyan]", default=True):
                    console.print("[yellow]Operation cancelled.[/yellow]")
                    raise typer.Exit()

            # Create the PDF
            success, message = pdf.create_pdf(file_path, text=content, image=image, force=force)

            if success:
                console.print(f"[green]✅ {message}[/green]")
            else:
                # Check if it's an overwrite issue
                if "already exists" in message and not force:
                    if Confirm.ask(f"[yellow]File exists. Overwrite {file_path}?[/yellow]"):
                        success, message = pdf.create_pdf(file_path, text=content, image=image, force=True)
                        if success:
                            console.print(f"[green]✅ {message}[/green]")
                        else:
                            console.print(f"[red]❌ {message}[/red]")
                            raise typer.Exit(1)
                    else:
                        console.print("[yellow]Operation cancelled.[/yellow]")
                        raise typer.Exit()
                else:
                    console.print(f"[red]❌ {message}[/red]")
                    raise typer.Exit(1)

        elif use_image:
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
            has_image = image is not None
            final_filename = detect.add_extension(filename, content, has_image)

            # Check if the detected format is PDF (shouldn't happen here, but just in case)
            if Path(final_filename).suffix.lower() == '.pdf':
                use_pdf = True
                file_path = Path(final_filename)
                console.print(f"[cyan]📄 Auto-detected mixed content. Creating PDF: {final_filename}[/cyan]")

                # Create the PDF
                success, message = pdf.create_pdf(file_path, text=content, image=image, force=force)

                if success:
                    console.print(f"[green]✅ {message}[/green]")
                else:
                    console.print(f"[red]❌ {message}[/red]")
                    raise typer.Exit(1)

                raise typer.Exit(0)  # Success, exit

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
    except typer.Exit:
        # Clean exit - just re-raise it
        raise
    except PermissionError:
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