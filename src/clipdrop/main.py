import re
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.syntax import Syntax
from rich.prompt import Confirm

from clipdrop import __version__
from clipdrop import clipboard, detect, files, images, pdf
from clipdrop.macos_ai import summarize_content, summarize_content_with_chunking
from clipdrop.error_helpers import display_error, show_success_message
from clipdrop.paranoid import (
    ParanoidMode,
    paranoid_gate,
    print_binary_skip_notice,
)
from clipdrop.exceptions import (
    YTDLPNotFoundError,
    NoCaptionsError,
    YouTubeError
)
from clipdrop.subtitles import to_srt, to_txt, to_md
from clipdrop.youtube import (
    validate_youtube_url,
    extract_video_id,
    list_captions,
    select_caption_track,
    download_vtt,
    get_video_info,
    vtt_to_srt,
    vtt_to_txt,
    vtt_to_md
)


# Standardized exit codes for audio transcription
class ExitCode:
    """Standardized exit codes for consistent error handling."""
    SUCCESS = 0
    NO_AUDIO = 1           # No audio found in clipboard
    PLATFORM_ERROR = 2     # Platform not supported (not macOS or wrong version)
    NO_SPEECH = 3          # Audio found but no speech detected
    TRANSCRIPTION_ERROR = 4  # General transcription failure

console = Console()


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation heuristics."""

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]
    if sentences:
        return sentences
    return [text.strip()] if text.strip() else []


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items[:3]) if items else "- None"


def generate_fallback_summary(content: str, note: str | None = None) -> str:
    """Generate a structured Markdown fallback summary."""

    sentences = _split_sentences(content)
    if not sentences:
        return ""

    overall = sentences[0]
    remaining = sentences[1:]

    questions = [sentence for sentence in remaining if "?" in sentence][:3]
    remaining = [sentence for sentence in remaining if sentence not in questions]

    action_keywords = [
        " should ",
        " need to ",
        " must ",
        " will ",
        " plan to ",
        " ensure ",
        " follow up",
        " schedule ",
        " consider ",
        " review ",
    ]

    actions: list[str] = []
    for sentence in remaining:
        lowered = f" {sentence.lower()} "
        if any(keyword in lowered for keyword in action_keywords):
            actions.append(sentence)
        if len(actions) == 3:
            break
    remaining = [sentence for sentence in remaining if sentence not in actions]

    takeaways = remaining[:3]

    note_line = f"> _{note}_\n\n" if note else ""

    return (
        f"{note_line}**Overall:** {overall}\n"
        f"### Key Takeaways\n{_bullet_list(takeaways)}\n"
        f"### Action Items\n{_bullet_list(actions)}\n"
        f"### Questions\n{_bullet_list(questions)}"
    )


def _write_summary_with_body(file_path: Path, summary_markdown: str, body: str) -> None:
    """Write summary at top of file with divider and original body."""

    summary = summary_markdown.strip()
    existing = body

    # Remove any existing summary block at the top separated by ---
    stripped = existing.lstrip()
    if stripped.startswith("**Overall:**") or stripped.startswith("## Summary"):
        parts = existing.split("\n---\n", 1)
        if len(parts) == 2:
            existing = parts[1].lstrip("\n")
        else:
            existing = ""

    combined = f"{summary}\n\n---\n\n{existing.lstrip()}".rstrip() + "\n"
    file_path.write_text(combined, encoding="utf-8")


def _normalize_summary_language(lang: Optional[str]) -> str:
    if not lang:
        return "en-US"

    cleaned = lang.strip()
    if len(cleaned) <= 2:
        mapping = {
            "en": "en-US",
            "es": "es-ES",
            "fr": "fr-FR",
            "de": "de-DE",
            "it": "it-IT",
            "pt": "pt-BR",
            "ja": "ja-JP",
            "ko": "ko-KR",
            "zh": "zh-CN",
        }
        return mapping.get(cleaned.lower(), "en-US")

    return cleaned


def _prepare_summary_source(content: str, content_format: str) -> tuple[str, str]:
    fmt = (content_format or "").lower()
    analysis_format = 'plaintext'
    text = content

    if fmt in {'srt', 'vtt'}:
        cleaned_lines: list[str] = []
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if fmt == 'srt':
                if line.isdigit():
                    continue
                if re.match(r"\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}", line):
                    continue
            else:  # vtt
                if line.upper() == 'WEBVTT':
                    continue
                if '-->' in line:
                    continue
            cleaned_lines.append(line)
        text = '\n'.join(cleaned_lines)
    elif fmt in {'md', 'markdown'}:
        analysis_format = 'markdown'
    elif fmt in {'html'}:
        analysis_format = 'html'

    if not text.strip():
        text = content

    return text, analysis_format


def summarize_document(
    *,
    content: str,
    file_path: Path,
    content_format: str,
    requested_lang: Optional[str],
    fallback_note: Optional[str] = None,
) -> None:
    console.print("🤖 Generating summary...", style="dim")

    summary_source, analysis_format = _prepare_summary_source(content, content_format)

    if not summary_source.strip():
        console.print("⚠️  Summarization skipped: no usable content", style="yellow")
        return

    is_suitable, reason = detect.is_summarizable_content(summary_source, analysis_format)
    reason_text = reason or ""

    use_chunking = False
    if not is_suitable:
        if reason_text == detect.SINGLE_PASS_LIMIT_REASON or len(content) > 15_000:
            use_chunking = True
        else:
            skip_reason = reason_text or "Content not suitable for summarization"
            console.print(f"⚠️  Summarization skipped: {skip_reason}", style="yellow")
            return
    elif len(content) > 15_000:
        use_chunking = True

    helper_format = content_format.lower() if content_format else "plaintext"
    if helper_format in {"txt", "text", "srt", "vtt"}:
        helper_format = "plaintext"
    elif helper_format == "md":
        helper_format = "markdown"

    language_for_summary = _normalize_summary_language(requested_lang)

    summary_result = None

    if use_chunking:
        total_length = len(summary_source)
        desired_chunks = max(6, min(20, total_length // 8000 + 1))
        chunk_char_limit = max(3000, min(5000, max(1, total_length // desired_chunks)))

        chunk_estimate = max(2, total_length // chunk_char_limit + 1)
        console.print(
            f"📄 Long content detected (~{chunk_estimate} sections)",
            style="dim",
        )
        console.print("🔄 Using multi-stage summarization...", style="dim")

        chunk_timeout = max(60, min(240, 30 + chunk_estimate * 8))
        fallback_chunk_info = chunk_estimate

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            task_id = progress.add_task("Summarizing sections...", total=100)
            summary_result = summarize_content_with_chunking(
                summary_source,
                content_format=analysis_format,
                language=language_for_summary,
                metadata={"source_filename": file_path.name},
                max_chunk_chars=chunk_char_limit,
                timeout=chunk_timeout,
            )
            progress.update(task_id, completed=100, description="Synthesizing final takeaways...")
    else:
        summary_result = summarize_content(summary_source)

    if summary_result is None:
        console.print("⚠️  Summarization skipped", style="yellow")
        return

    final_summary: Optional[str] = None
    final_warnings: list[str] = list(summary_result.warnings or [])
    final_stage_results = summary_result.stage_results
    message_style = "green"
    message_text = "✨ Summary added to file"

    if summary_result.success and summary_result.summary:
        final_summary = summary_result.summary
    else:
        failure_reason = summary_result.error or "Summarization failed"
        if summary_result.retryable:
            failure_reason += " (try again shortly)"
        if summary_result.stage:
            failure_reason += f" [stage: {summary_result.stage}]"

        fallback_summary = generate_fallback_summary(
            summary_source,
            note=fallback_note or f"Fallback summary generated locally (source: {failure_reason})",
        )
        if fallback_summary:
            final_summary = fallback_summary
            final_warnings.append(f"Fallback summary used ({failure_reason})")
            message_text = "✨ Summary added via fallback"
            if use_chunking:
                processed = fallback_chunk_info or 0
                fallback_stage = {
                    "stage": "fallback",
                    "status": "ok",
                    "processed": processed,
                }
                if final_stage_results:
                    final_stage_results = list(final_stage_results) + [fallback_stage]
                else:
                    final_stage_results = [fallback_stage]
        else:
            console.print(f"❌ Summarization failed: {failure_reason}", style="red")
            return

    if final_stage_results:
        console.print("📊 Summarization stages:", style="dim")
        for stage_info in final_stage_results:
            stage_name = stage_info.get("stage", "?")
            status = stage_info.get("status", "pending")
            processed = stage_info.get("processed")
            details = f" - {stage_name}: {status}"
            if processed:
                details += f" ({processed} chunks)"
            console.print(details, style="dim")

    for warning in final_warnings:
        console.print(f"⚠️  {warning}", style="yellow")

    if final_summary:
        _write_summary_with_body(file_path, final_summary, content)
        console.print(message_text, style=message_style)


def add_chapter_markers(content: str, chapters: Optional[list], format: str) -> str:
    """
    Add chapter markers to transcript content.

    Args:
        content: The transcript content
        chapters: List of chapter dictionaries with 'title' and 'start_time' keys
        format: The output format (.srt, .vtt, .txt, .md)

    Returns:
        Content with chapter markers added
    """
    if not chapters:
        return content

    # Build chapter header based on format
    chapter_text = "\n=== CHAPTERS ===\n"
    for chapter in chapters:
        start_time = chapter.get('start_time', 0)
        title = chapter.get('title', 'Chapter')
        # Convert seconds to HH:MM:SS format
        hours = int(start_time // 3600)
        minutes = int((start_time % 3600) // 60)
        seconds = int(start_time % 60)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        chapter_text += f"{time_str} - {title}\n"
    chapter_text += "================\n\n"

    if format == '.md':
        # For Markdown, use proper header formatting
        chapter_text = "\n## Chapters\n\n"
        for chapter in chapters:
            start_time = chapter.get('start_time', 0)
            title = chapter.get('title', 'Chapter')
            hours = int(start_time // 3600)
            minutes = int((start_time % 3600) // 60)
            seconds = int(start_time % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            chapter_text += f"- **{time_str}** - {title}\n"
        chapter_text += "\n"
    elif format == '.vtt':
        # For VTT, add as a NOTE block at the beginning
        chapter_text = "NOTE\nCHAPTERS:\n"
        for chapter in chapters:
            start_time = chapter.get('start_time', 0)
            title = chapter.get('title', 'Chapter')
            hours = int(start_time // 3600)
            minutes = int((start_time % 3600) // 60)
            seconds = int(start_time % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            chapter_text += f"{time_str} - {title}\n"
        chapter_text += "\n"
        # Insert after WEBVTT header if present
        if content.startswith('WEBVTT'):
            lines = content.split('\n', 2)
            if len(lines) >= 2:
                content = lines[0] + '\n' + lines[1] + '\n\n' + chapter_text + (lines[2] if len(lines) > 2 else '')
            else:
                content = content + '\n\n' + chapter_text
        else:
            content = chapter_text + content
        return content

    # For all other formats, prepend the chapter list
    return chapter_text + content


def generate_auto_filename(content: Optional[str], provided_filename: Optional[str]) -> Optional[str]:
    """Build a descriptive filename from content for --auto-name.

    Uses the on-device model for the title when available, falling back to a
    heuristic slug of the content. A provided extension is honored; otherwise
    the extension is chosen by format detection.

    Returns the full filename, or None if no usable name could be derived.
    """
    base = (content or "").strip()
    if not base:
        return None

    title = None
    try:
        from clipdrop.macos_ai import suggest_filename as ai_suggest
        title = ai_suggest(base)
    except Exception:
        title = None

    stem = files.slugify(title) if title else ""
    if not stem:
        # Fall back to a heuristic slug derived from the content itself.
        stem = files.slugify(base)
    if not stem:
        return None

    provided_ext = Path(provided_filename).suffix if provided_filename else ""
    ext = provided_ext or f".{detect.detect_format(content)}"
    return f"{stem}{ext}"


def _table_dimensions(table: dict) -> tuple[list[str], list, int]:
    headers = [str(h) for h in (table.get("headers") or [])]
    rows = table.get("rows") or []
    width = len(headers) or (len(rows[0]) if rows and isinstance(rows[0], list) else 0)
    if not headers and width:
        headers = [f"Column {i + 1}" for i in range(width)]
    return headers, rows, width


def _normalize_cells(cells, width: int) -> list[str]:
    values = [str(c) for c in (cells if isinstance(cells, list) else [cells])][:width]
    values += [""] * (width - len(values))
    return values


def render_markdown_table(table: dict) -> str:
    """Render a {headers, rows} table dict as a GitHub-flavored Markdown table."""
    headers, rows, width = _table_dimensions(table)
    if not width:
        return ""

    def fmt(cells) -> str:
        escaped = [c.replace("|", "\\|") for c in _normalize_cells(cells, width)]
        return "| " + " | ".join(escaped) + " |"

    lines = [fmt(headers), "| " + " | ".join(["---"] * width) + " |"]
    lines.extend(fmt(row) for row in rows)
    return "\n".join(lines) + "\n"


def render_csv_table(table: dict) -> str:
    """Render a {headers, rows} table dict as CSV."""
    import csv
    import io

    headers, rows, width = _table_dimensions(table)
    if not width:
        return ""

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if headers:
        writer.writerow(headers)
    for row in rows:
        writer.writerow(_normalize_cells(row, width))
    return buffer.getvalue()


def version_callback(value: bool):
    """Handle --version flag."""
    if value:
        console.print(f"[cyan]clipdrop version {__version__}[/cyan]")
        raise typer.Exit()


def handle_audio_transcription(
    filename: Optional[str] = None,
    paranoid_flag: bool = False,
    lang: Optional[str] = None,
    summarize: bool = False,
) -> None:
    """
    Handle transcription of audio from clipboard.

    Args:
        filename: Optional output filename
        paranoid_flag: Whether to apply paranoid mode
        lang: Optional language code (e.g., 'en-US')
    """
    try:
        from clipdrop.macos_ai import (
            transcribe_from_clipboard_stream,
            UnsupportedPlatformError,
            UnsupportedMacOSVersionError,
            HelperNotFoundError
        )

        # Determine output filename and format
        if filename:
            output_path = Path(filename)
            ext = output_path.suffix.lower() or '.srt'
            final_filename = filename
        else:
            # Generate default filename with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_filename = f"transcript_{timestamp}.srt"
            ext = '.srt'

        console.print("[cyan]🎵 Audio detected in clipboard[/cyan]")
        console.print(f"[dim]Output: {final_filename}[/dim]\n")

        # Collect segments with progress display
        segments = []
        total_duration = 0.0

        def progress_callback(segment: dict, count: int) -> None:
            nonlocal total_duration
            total_duration = max(total_duration, segment.get('end', 0))

        # Use Rich status for progress display
        with console.status("[bold cyan]Transcribing audio...[/bold cyan]") as status:
            try:
                for segment in transcribe_from_clipboard_stream(lang=lang, progress_callback=progress_callback):
                    segments.append(segment)
                    # Update status with segment count and duration
                    if total_duration:
                        hours = int(total_duration // 3600)
                        minutes = int((total_duration % 3600) // 60)
                        seconds = int(total_duration % 60)
                        duration_str = f" {hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        duration_str = ""
                    status.update(
                        f"[bold cyan]Transcribing... [{len(segments)} segments]{duration_str}[/bold cyan]"
                    )
            except RuntimeError as e:
                if "No audio" in str(e):
                    console.print("[red]❌ No audio found in clipboard[/red]")
                    console.print("[dim]Please copy an audio file first, then try again.[/dim]")
                    raise typer.Exit(ExitCode.NO_AUDIO)
                elif "macOS" in str(e) or "platform" in str(e).lower():
                    console.print("[red]❌ Audio transcription requires macOS 26.0+[/red]")
                    console.print("[dim]This feature uses on-device Apple Intelligence.[/dim]")
                    raise typer.Exit(ExitCode.PLATFORM_ERROR)
                else:
                    console.print(f"[red]❌ Transcription failed: {e}[/red]")
                    raise typer.Exit(ExitCode.TRANSCRIPTION_ERROR)

        if not segments:
            console.print("[yellow]⚠️  No speech detected in audio[/yellow]")
            raise typer.Exit(ExitCode.NO_SPEECH)

        # Format output based on extension
        if ext in ('.srt', ''):
            content = to_srt(segments)
        elif ext == '.txt':
            content = to_txt(segments)
        elif ext == '.md':
            content = to_md(segments)
        else:
            console.print(f"[yellow]⚠️  Unknown format {ext}, using SRT[/yellow]")
            content = to_srt(segments)

        # Apply paranoid mode if requested
        if paranoid_flag:
            content = paranoid_gate(content, mode=ParanoidMode.SILENT)

        # Save the file
        try:
            Path(final_filename).write_text(content, encoding='utf-8')
            console.print(f"\n[green]✅ Saved transcript to {final_filename}[/green]")

            # Show summary
            console.print(f"[dim]Total segments: {len(segments)}[/dim]")
            if total_duration:
                hours = int(total_duration // 3600)
                minutes = int((total_duration % 3600) // 60)
                seconds = int(total_duration % 60)
                console.print(f"[dim]Duration: {hours:02d}:{minutes:02d}:{seconds:02d}[/dim]")

            if summarize:
                summarize_document(
                    content=content,
                    file_path=Path(final_filename),
                    content_format=ext.lstrip('.') or 'srt',
                    requested_lang=lang,
                    fallback_note="Fallback summary generated for audio transcript",
                )

        except Exception as e:
            display_error(e, final_filename)
            raise typer.Exit(ExitCode.TRANSCRIPTION_ERROR)

    except UnsupportedPlatformError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print("[yellow]This feature requires macOS with Apple Intelligence[/yellow]")
        raise typer.Exit(ExitCode.PLATFORM_ERROR)

    except UnsupportedMacOSVersionError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print("[yellow]Please upgrade to macOS 26.0 or later[/yellow]")
        raise typer.Exit(ExitCode.PLATFORM_ERROR)

    except HelperNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(ExitCode.TRANSCRIPTION_ERROR)

    except ImportError as e:
        # Fallback for any other import issues
        console.print("[red]❌ Audio transcription module not available[/red]")
        console.print(f"[yellow]Error: {e}[/yellow]")
        raise typer.Exit(ExitCode.PLATFORM_ERROR)


def handle_youtube_transcript(
    filename: Optional[str],
    scan: bool = False,
    force: bool = False,
    preview: bool = False,
    paranoid_mode: Optional[ParanoidMode] = None,
    lang: Optional[str] = None,
    yes: bool = False,
    chapters: bool = False,
    summarize: bool = False,
) -> None:
    """
    Handle YouTube transcript download command.

    Args:
        filename: Target filename (optional - defaults to video title)
        scan: Whether paranoid mode is enabled via flag
        force: Whether to force overwrite existing files
        preview: Whether to preview content before saving
        paranoid_mode: Paranoid mode setting
        lang: Preferred subtitle language code
        yes: Whether to auto-accept paranoid prompts
        chapters: Whether to include chapter markers in transcript
    """
    # Get clipboard content
    url = clipboard.get_text()
    if not url or not url.strip():
        display_error('empty_clipboard')
        raise typer.Exit(1)

    url = url.strip()

    # Validate YouTube URL
    if not validate_youtube_url(url):
        console.print("[red]❌ No YouTube URL in clipboard[/red]")
        if len(url) > 100:
            console.print(f"[yellow]Found: {url[:100]}...[/yellow]")
        else:
            console.print(f"[yellow]Found: {url}[/yellow]")
        console.print("\n[dim]Please copy a YouTube URL first, then try again.[/dim]")
        console.print("[dim]Examples: youtube.com/watch?v=..., youtu.be/..., youtube.com/shorts/...[/dim]")
        raise typer.Exit(1)

    try:
        # Extract video ID and get video info
        video_id = extract_video_id(url)
        console.print(f"[cyan]🎥 Found YouTube video: {video_id}[/cyan]")

        # Get video information
        video_info = get_video_info(url)
        title = video_info.get('title', 'Unknown Title')
        console.print(f"[cyan]📺 Title: {title}[/cyan]")

        # List available captions
        console.print("[cyan]🔍 Checking available captions...[/cyan]")
        captions = list_captions(url)

        if not captions:
            raise NoCaptionsError(video_id)

        # Select caption track
        selected = select_caption_track(captions, lang)
        if not selected:
            # Show available languages to help user
            if lang:
                console.print(f"[yellow]⚠️ No captions found for language: '{lang}'[/yellow]")
                console.print("\n[cyan]Available languages:[/cyan]")
                for cap_lang, cap_name, is_auto in captions:
                    auto_text = " (auto-generated)" if is_auto else ""
                    console.print(f"  • {cap_lang}: {cap_name}{auto_text}")
                console.print("\n[dim]Tip: Use --lang with one of the language codes above[/dim]")
            raise NoCaptionsError(f"No captions available for language: {lang}")

        lang_code, lang_name, is_auto = selected
        caption_type = "(auto-generated)" if is_auto else "(manual)"
        console.print(f"[green]✓ Selected: {lang_name} {caption_type}[/green]")

        # Download VTT
        console.print("[cyan]📥 Downloading captions...[/cyan]")
        vtt_path = download_vtt(url, lang_code)

        # Read VTT content
        with open(vtt_path, 'r', encoding='utf-8') as f:
            vtt_content = f.read()

        # Determine output filename and format
        if filename:
            # Use provided filename
            file_path = Path(filename)
            if file_path.suffix:
                ext = file_path.suffix.lower()
                output_filename = filename
            else:
                # Default to .srt if no extension
                ext = '.srt'
                output_filename = f"{filename}.srt"
        else:
            # Use video title as filename
            from .youtube import sanitize_filename
            safe_title = sanitize_filename(title)
            ext = '.srt'  # Default format
            output_filename = f"{safe_title}.srt"

        # Convert to requested format
        if ext == '.srt':
            content = vtt_to_srt(vtt_content)
        elif ext == '.vtt':
            content = vtt_content
        elif ext == '.txt':
            content = vtt_to_txt(vtt_content)
        elif ext == '.md':
            content = vtt_to_md(vtt_content)
        else:
            # Default to SRT for unknown extensions
            content = vtt_to_srt(vtt_content)
            console.print(f"[yellow]⚠️ Unknown format '{ext}', using SRT format[/yellow]")

        # Add chapter markers if requested and available
        if chapters:
            video_chapters = video_info.get('chapters')
            if video_chapters:
                console.print(f"[cyan]📑 Adding {len(video_chapters)} chapter markers...[/cyan]")
                content = add_chapter_markers(content, video_chapters, ext)
            elif chapters:
                console.print("[yellow]⚠️ No chapters available for this video[/yellow]")

        # Apply paranoid mode if enabled (skip for VTT to preserve format)
        active_paranoid = paranoid_mode or (ParanoidMode.PROMPT if scan else None)
        if active_paranoid and ext in ['.txt', '.md', '.srt']:
            content, _ = paranoid_gate(
                content,
                active_paranoid,
                is_tty=sys.stdin.isatty(),
                auto_yes=yes
            )
            if content is None:
                console.print("[yellow]⚠️ Content not saved (paranoid mode)[/yellow]")
                raise typer.Exit(0)

        # Preview if requested
        if preview:
            console.print("\n[bold cyan]Preview:[/bold cyan]")
            preview_lines = content.split('\n')[:20]
            for line in preview_lines:
                console.print(f"  {line}")
            if len(content.split('\n')) > 20:
                total_lines = len(content.split('\n'))
                console.print(f"  [dim]... ({total_lines} total lines)[/dim]")

            if not Confirm.ask("\n[yellow]Save this content?[/yellow]"):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        # Check if file exists and handle overwrite
        output_path = Path(output_filename)
        if output_path.exists() and not force:
            if not Confirm.ask(f"[yellow]File '{output_filename}' already exists. Overwrite?[/yellow]"):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        # Save the file
        files.write_text(output_filename, content, force=True)

        # Show success message
        console.print(f"[green]✅ Transcript saved to '{output_filename}'[/green]")
        file_size = len(content.encode('utf-8'))
        size_str = f"{file_size:,} bytes" if file_size < 1024 else f"{file_size/1024:.1f} KB"
        console.print(f"[dim]   Format: {ext[1:].upper()} | Size: {size_str} | Language: {lang_name}[/dim]")

        if summarize:
            summarize_document(
                content=content,
                file_path=output_path,
                content_format=ext.lstrip('.'),
                requested_lang=lang,
                fallback_note="Fallback summary generated for YouTube transcript",
            )

    except YTDLPNotFoundError:
        console.print("[red]❌ yt-dlp is not installed[/red]")
        console.print("[yellow]Install with: pip install 'clipdrop[youtube]'[/yellow]")
        console.print("[dim]Or: pip install yt-dlp[/dim]")
        raise typer.Exit(1)
    except NoCaptionsError as e:
        console.print(f"[red]❌ {str(e)}[/red]")
        console.print("[dim]This video may not have captions available.[/dim]")
        raise typer.Exit(1)
    except YouTubeError as e:
        console.print(f"[red]❌ YouTube error: {str(e)}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {str(e)}[/red]")
        raise typer.Exit(1)


def main(
    filename: Optional[str] = typer.Argument(
        None,
        help="Target filename. Extension optional - auto-detects format. "
             "Examples: 'notes' → notes.txt, 'data' → data.json, "
             "'screenshot' → screenshot.png, 'meeting' → meeting.srt (if audio in clipboard)"
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
    append: bool = typer.Option(
        False,
        "--append",
        "-a",
        help="Append to existing file instead of overwriting. Text-only operation. "
             "Adds content to the end of file with smart separation based on file type"
    ),
    scan: bool = typer.Option(
        False,
        "--scan",
        "-s",
        help="Scan for secrets before saving (interactive prompt)",
    ),
    scan_mode: Optional[ParanoidMode] = typer.Option(
        None,
        "--scan-mode",
        help="How to handle found secrets: prompt, redact, block, warn",
        show_choices=True,
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Auto-accept all prompts (useful for automation)",
    ),
    text_only: bool = typer.Option(
        False,
        "--text-only",
        help="Save only text content, ignore images in clipboard"
    ),
    image_only: bool = typer.Option(
        False,
        "--image-only",
        help="Save only image content, ignore text in clipboard"
    ),
    ocr: bool = typer.Option(
        False,
        "--ocr",
        help="Extract text from a clipboard image using on-device OCR "
             "(macOS) and save it as text. Composes with --summarize and "
             "secret scanning. Use --lang for recognition hints (e.g. en-US)"
    ),
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        help="Language code for transcription/captions. "
             "YouTube: 'en', 'es', 'fr', etc. (150+ languages). "
             "Audio transcription: 'en-US', 'es-ES', 'ja-JP', etc. "
             "Auto-detects if not specified"
    ),
    chapters: bool = typer.Option(
        False,
        "--chapters",
        help="Include YouTube chapter markers in transcript. "
             "Adds timestamps and chapter titles as headers (Markdown) "
             "or comments (SRT/VTT/TXT)"
    ),
    summarize: bool = typer.Option(
        False,
        "--summarize",
        "-S",
        help="Generate an on-device summary and append it to saved text",
    ),
    auto_name: bool = typer.Option(
        False,
        "--auto-name",
        help="Let ClipDrop name the file from its content (on-device). "
             "A provided extension is kept; the filename can be omitted entirely",
    ),
    rewrite: Optional[str] = typer.Option(
        None,
        "--rewrite",
        help="Rewrite clipboard text in a style before saving (on-device), "
             "e.g. --rewrite formal | concise | friendly | professional",
        metavar="STYLE",
    ),
    prompt: Optional[str] = typer.Option(
        None,
        "--prompt",
        help="Transform clipboard text with a freeform instruction before "
             "saving (on-device), e.g. --prompt \"turn this into release notes\"",
        metavar="INSTRUCTION",
    ),
    to_table: bool = typer.Option(
        False,
        "--to-table",
        help="Turn clipboard text into a table (on-device). Saves Markdown by "
             "default, or CSV when the filename ends in .csv",
    ),
    fetch_remote_images: bool = typer.Option(
        False,
        "--fetch-remote-images",
        help="When building a PDF from copied web content, download remote "
             "(http/https) images. Off by default for privacy; embedded "
             "(data:) images are always included",
    ),
    youtube: bool = typer.Option(
        False,
        "--youtube",
        "-yt",
        help="Download YouTube transcript from clipboard URL. "
             "Supports multiple formats: .srt (subtitles), .vtt (WebVTT), "
             ".txt (plain text), .md (markdown with timestamps). "
             "Use --lang for specific language (150+ supported)"
    ),
    audio: bool = typer.Option(
        False,
        "--audio",
        help="Force audio transcription mode (usually auto-detected). "
             "Outputs: .srt (subtitles), .txt (plain text), or .md (markdown). "
             "Requires macOS 26.0+ with Apple Intelligence"
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
    It handles text, images, audio (macOS 26.0+), and mixed content with intelligent
    format detection for JSON, Markdown, CSV, and various media formats.

    [bold cyan]Quick Examples:[/bold cyan]

      [green]Text:[/green]
        clipdrop notes              # Auto-detects format → notes.txt
        clipdrop data               # JSON detected → data.json
        clipdrop readme             # Markdown detected → readme.md

      [green]Images:[/green]
        clipdrop screenshot         # Saves clipboard image → screenshot.png
        clipdrop photo.jpg          # Saves as JPEG with optimization

      [green]Audio (macOS 26.0+):[/green]
        clipdrop                    # Auto-transcribes audio → transcript_[timestamp].srt
        clipdrop meeting.txt        # Transcribe to plain text
        clipdrop notes.md           # Transcribe to markdown
        clipdrop --audio talk.srt   # Force transcription mode

      [green]YouTube:[/green]
        clipdrop --youtube          # Download transcript from clipboard URL
        clipdrop -yt video.srt      # Save as subtitles
        clipdrop -yt --lang es      # Spanish transcript
        clipdrop -yt --chapters     # Include chapter markers

      [green]Mixed Content:[/green]
        clipdrop document           # Mixed text+image → document.pdf
        clipdrop content --text-only # Forces text mode
        clipdrop report.pdf         # Explicitly create PDF

    [bold cyan]Smart Features:[/bold cyan]

      • Auto-detects JSON, Markdown, CSV formats
      • On-device audio transcription (macOS 26.0+ with Apple Intelligence)
      • YouTube transcript downloads (150+ languages)
      • Optimizes images (PNG/JPEG compression)
      • Handles mixed clipboard content intelligently
      • Protects against accidental overwrites
      • Optional paranoid mode to detect secrets before saving
      • Shows preview before saving

    [bold cyan]Common Workflows:[/bold cyan]

      1. Copy code/text → clipdrop script.py
      2. Take screenshot → clipdrop screenshot.png
      3. Copy JSON API response → clipdrop response.json
      4. Copy markdown notes → clipdrop notes.md
      5. Copy audio file → clipdrop (auto-transcribes)
      6. Copy YouTube URL → clipdrop --youtube
      7. Copy sensitive text → clipdrop secrets.txt -s (scan before saving)

    [dim]For more help, visit: https://github.com/prateekjain24/clipdrop[/dim]
    """
    # Define paranoid variables for compatibility
    paranoid_flag = scan
    paranoid_mode = scan_mode

    # Check if this is transcribe mode (explicit flag)
    if audio:
        return handle_audio_transcription(
            filename=filename,
            paranoid_flag=paranoid_flag,
            lang=lang,
            summarize=summarize,
        )

    # Check if this is YouTube mode
    if youtube:
        return handle_youtube_transcript(
            filename=filename,  # Can be None for YouTube mode
            scan=paranoid_flag,
            force=force,
            preview=preview,
            paranoid_mode=paranoid_mode,
            lang=lang,
            yes=yes,
            chapters=chapters,
            summarize=summarize,
        )

    # Check for audio in clipboard (with or without filename)
    try:
        from clipdrop.macos_ai import check_audio_in_clipboard
        if check_audio_in_clipboard():
            console.print("[cyan]🎵 Audio detected in clipboard[/cyan]")
            return handle_audio_transcription(
                filename=filename,
                paranoid_flag=paranoid_flag,
                lang=lang,
                summarize=summarize,
            )
    except (ImportError, RuntimeError):
        pass  # Not on macOS or helper not available

    # If no filename provided and no audio detected, show help
    # (unless --auto-name will derive one from the content later)
    if filename is None and not auto_name:
        console.print("\n[red]📝 Please provide a filename[/red]")
        console.print("[yellow]Usage: clipdrop [OPTIONS] FILENAME[/yellow]")
        console.print("\n[dim]Examples:[/dim]")
        console.print("  clipdrop notes.txt     # Save text")
        console.print("  clipdrop image.png     # Save image")
        console.print("  clipdrop data.json     # Save JSON")
        console.print("  clipdrop --youtube     # Download YouTube transcript")
        console.print("  clipdrop --audio       # Transcribe audio from clipboard")
        console.print("  clipdrop -yt output.srt # YouTube with custom name")
        console.print("\n[dim]Try 'clipdrop --help' for more options[/dim]")
        raise typer.Exit(1)

    try:
        # Determine content type in clipboard
        content_type = clipboard.get_content_type()
        active_paranoid = paranoid_mode or (ParanoidMode.PROMPT if paranoid_flag else None)

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
                    enhanced_chunks = html_parser.parse_html_content_enhanced(
                        html_content, allow_remote=fetch_remote_images
                    )
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
                        enhanced_chunks, file_path, educational_mode=True
                    )

                    # Success message
                    file_size = file_path.stat().st_size
                    size_str = files.get_file_size_human(file_size)
                    console.print(f"[green]✅ Created enhanced PDF ({total_text_len} chars, {len(content_counts)} content types, {size_str}) at {file_path}[/green]")
                    raise typer.Exit()

                else:
                    # Fall back to standard ordered parsing
                    ordered_chunks = html_parser.parse_html_content_ordered(
                        html_content, allow_remote=fetch_remote_images
                    )

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

        # Check for conflicting flags
        if text_only and image_only:
            console.print("[red]❌ Cannot use both --text-only and --image-only.[/red]")
            raise typer.Exit(1)

        # Get both text and image content (may be None)
        content = clipboard.get_text()
        image = clipboard.get_image()

        # OCR mode - extract text from a clipboard image and treat it as text
        if ocr:
            if image is None:
                console.print("[red]❌ No image in clipboard to run OCR on.[/red]")
                console.print("[dim]Copy a screenshot or image, then try again.[/dim]")
                raise typer.Exit(1)

            from clipdrop.macos_ai import ocr_image, OCRNotAvailableError

            console.print("[cyan]🔎 Extracting text from image (on-device OCR)...[/cyan]")
            try:
                recognized = ocr_image(image, lang=lang)
            except OCRNotAvailableError as exc:
                console.print(f"[red]❌ {exc}[/red]")
                raise typer.Exit(2)
            except RuntimeError as exc:
                console.print(f"[red]❌ OCR failed: {exc}[/red]")
                raise typer.Exit(1)

            if not recognized.strip():
                console.print("[yellow]⚠️  No text detected in image[/yellow]")
                raise typer.Exit(1)

            console.print(f"[green]✓ Extracted {len(recognized)} characters[/green]")
            content = recognized
            image = None
            content_type = 'text'

        # Transform mode - rewrite / freeform prompt / to-table over text content
        transform_ops = [
            name for name, value in (
                ("rewrite", rewrite),
                ("prompt", prompt),
                ("table", to_table),
            ) if value
        ]
        if len(transform_ops) > 1:
            console.print("[red]❌ Use only one transform at a time (--rewrite / --prompt / --to-table).[/red]")
            raise typer.Exit(1)

        if transform_ops:
            transform_op = transform_ops[0]
            if not content or not content.strip():
                console.print("[red]❌ No text content to transform.[/red]")
                console.print("[dim]Copy text (or use --ocr on an image) before --rewrite/--prompt/--to-table.[/dim]")
                raise typer.Exit(1)

            from clipdrop.macos_ai import transform_content, TransformNotAvailableError

            labels = {"rewrite": "Rewriting", "prompt": "Transforming", "table": "Building table from"}
            console.print(f"[cyan]✍️  {labels[transform_op]} content (on-device)...[/cyan]")
            try:
                data = transform_content(
                    content,
                    transform_op,
                    style=rewrite,
                    instruction=prompt,
                    language=lang,
                )
            except TransformNotAvailableError as exc:
                console.print(f"[red]❌ {exc}[/red]")
                raise typer.Exit(2)
            except RuntimeError as exc:
                console.print(f"[red]❌ Transform failed: {exc}[/red]")
                raise typer.Exit(1)

            if transform_op == "table":
                table = data.get("table") or {}
                target_ext = Path(filename).suffix.lower() if filename else ""
                content = render_csv_table(table) if target_ext == ".csv" else render_markdown_table(table)
            else:
                content = data.get("result", "")

            if not content or not content.strip():
                console.print("[yellow]⚠️  Transform produced no output[/yellow]")
                raise typer.Exit(1)

            image = None
            content_type = 'text'
            console.print("[green]✓ Transformed[/green]")

        # Auto-name the file from its content when requested
        if auto_name:
            generated = generate_auto_filename(content, filename)
            if generated:
                filename = generated
                console.print(f"[cyan]🏷️  Auto-named file: {filename}[/cyan]")
            elif filename is None:
                console.print("[red]❌ Could not auto-name: no text content to derive a name from.[/red]")
                console.print("[dim]Provide a filename, or combine --auto-name with text/--ocr content.[/dim]")
                raise typer.Exit(1)

        # Handle append mode - force text-only
        if append:
            if not content:
                console.print("[red]❌ No text found in clipboard for append operation.[/red]")
                console.print("[dim]Note: Append mode only works with text content.[/dim]")
                raise typer.Exit(1)

            # Force text mode, ignore images
            image = None
            console.print("[cyan]📝 Append mode - using text content only[/cyan]")

        # Check if user explicitly wants PDF
        file_path = Path(filename)
        wants_pdf = file_path.suffix.lower() == '.pdf'

        # Prevent PDF with append mode
        if append and wants_pdf:
            console.print("[red]❌ Cannot append to PDF files.[/red]")
            console.print("[dim]Append mode only works with text files.[/dim]")
            raise typer.Exit(1)

        # Determine what to save based on content and user preference
        use_pdf = False
        use_image = False

        if wants_pdf:
            # User explicitly requested PDF
            use_pdf = True
            console.print("[cyan]📄 Creating PDF from clipboard content...[/cyan]")
        elif content_type == 'both':
            # Both image and text exist
            if text_only:
                console.print("[cyan]ℹ️  Both image and text found. Using text only.[/cyan]")
                image = None  # Ignore image in text-only mode
            elif image_only:
                console.print("[cyan]ℹ️  Both image and text found. Using image only.[/cyan]")
                content = None  # Ignore text in image-only mode
                use_image = True
            elif not file_path.suffix:
                # No extension provided, mixed content -> suggest PDF
                use_pdf = True
                console.print("[cyan]📄 Mixed content detected (text + image). Creating PDF to preserve both.[/cyan]")
            else:
                # Has extension, follow user's choice
                if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
                    use_image = True
                    content = None  # Use image only
                    console.print("[cyan]ℹ️  Both found. Using image (use --text-only for text).[/cyan]")
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
            if active_paranoid is not None:
                print_binary_skip_notice(active_paranoid)

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

            if active_paranoid is not None:
                content, _ = paranoid_gate(
                    content,
                    active_paranoid,
                    is_tty=sys.stdin.isatty(),
                    auto_yes=yes,
                )

            # Show preview if requested
            if preview:
                preview_content = content[:200] if content else None
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

            # Write or append the file
            if append:
                # Check if file exists for informative message
                file_existed = file_path.exists()

                # Apply paranoid mode to content being appended (if enabled)
                if active_paranoid is not None and not file_existed:
                    # Only scan on new files in append mode
                    content, _ = paranoid_gate(
                        content,
                        active_paranoid,
                        is_tty=sys.stdin.isatty(),
                        auto_yes=yes,
                    )

                # Perform append operation
                bytes_appended = files.append_text_to_file(file_path, content)

                # Show append-specific success message
                size_str = files.get_file_size_human(bytes_appended)
                if file_existed:
                    console.print(f"[green]✅ Appended {size_str} to {file_path}[/green]")
                else:
                    console.print(f"[green]✅ Created new file with {size_str}: {file_path}[/green]")
            else:
                # Normal write operation
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

                if summarize:
                    summarize_document(
                        content=content,
                        file_path=file_path,
                        content_format=content_format,
                        requested_lang=lang,
                        fallback_note="Fallback summary generated locally",
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
    help="Save clipboard content to files with smart format detection.\n\n"
         "📋 → 📄 Transform your clipboard into files with one command.\n\n"
         "Features: Audio transcription (macOS 26.0+), YouTube transcripts, "
         "PDF generation, smart format detection (JSON/Markdown/CSV), "
         "image optimization, and secret scanning.",
    add_completion=False,
    rich_markup_mode="rich",
)

# Register main function as the only command
app.command()(main)

if __name__ == "__main__":
    app()
