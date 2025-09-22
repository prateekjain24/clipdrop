import pytest
import typer
from rich.console import Console

from clipdrop.paranoid import ParanoidMode, paranoid_gate, scan_text


def test_scan_text_detects_signature():
    text = "Here is an AWS key: AKIAABCDEFGHIJKLMNOP"
    findings, truncated, limit_hit = scan_text(text)

    assert not truncated
    assert not limit_hit
    assert any(f.kind == "aws_access_key_id" for f in findings)


def test_scan_text_keyname_heuristic():
    text = "password: SuperSecretValue1234"
    findings, _, _ = scan_text(text)

    assert any(f.kind.startswith("keyname_password") for f in findings)


def test_scan_text_high_entropy_detection():
    candidate = "S1u9hD3kLmP8Qr4StUvWxYz12+/="
    findings, _, _ = scan_text(candidate)

    assert any(f.kind == "high_entropy" for f in findings)


def test_scan_text_skips_hex_sequences():
    hex_sample = "0123456789abcdef0123456789abcdef"
    findings, _, _ = scan_text(hex_sample)

    assert findings == []


def test_paranoid_gate_warn_leaves_text():
    text = "Token sk-ABCDEFGHIJKLMNOPQRSTUVWX"
    result, action = paranoid_gate(
        text,
        ParanoidMode.WARN,
        is_tty=True,
        auto_yes=False,
        console=Console(record=True),
    )

    assert result == text
    assert action == "save"


def test_paranoid_gate_redact():
    text = "sk-ABCDEFGHIJKLMNOPQRSTUVWX"
    result, action = paranoid_gate(
        text,
        ParanoidMode.REDACT,
        is_tty=True,
        auto_yes=False,
        console=Console(record=True),
    )

    assert action == "redact"
    assert "REDACTED" in result


def test_paranoid_gate_prompt_abort(monkeypatch):
    text = "sk-ABCDEFGHIJKLMNOPQRSTUVWX"
    recorded_console = Console(record=True)

    monkeypatch.setattr(recorded_console, "input", lambda *args, **kwargs: "a")

    with pytest.raises(typer.Exit) as exc:
        paranoid_gate(
            text,
            ParanoidMode.PROMPT,
            is_tty=True,
            auto_yes=False,
            console=recorded_console,
        )

    assert exc.value.exit_code == 18


def test_paranoid_gate_prompt_auto_yes():
    text = "sk-ABCDEFGHIJKLMNOPQRSTUVWX"
    result, action = paranoid_gate(
        text,
        ParanoidMode.PROMPT,
        is_tty=True,
        auto_yes=True,
        console=Console(record=True),
    )

    assert result == text
    assert action == "save"


def test_paranoid_gate_non_tty_blocks():
    text = "sk-ABCDEFGHIJKLMNOPQRSTUVWX"

    with pytest.raises(typer.Exit) as exc:
        paranoid_gate(
            text,
            ParanoidMode.PROMPT,
            is_tty=False,
            auto_yes=False,
            console=Console(record=True),
        )

    assert exc.value.exit_code == 17
