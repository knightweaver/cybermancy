#!/usr/bin/env python3
"""
transcribe_zoom_recording.py

Transcribe a long Zoom audio recording with the OpenAI Audio Transcriptions API.

Features
--------
- Accepts long .m4a/.mp3/.wav/.mp4 recordings.
- Uses ffmpeg to split/re-encode audio into small API-safe MP3 chunks.
- Transcribes chunks sequentially with an OpenAI transcription model.
- Writes:
    <stem>_transcript.txt
    <stem>_transcript.md
- Adds absolute recording timestamps at each chunk boundary.
- Saves each chunk transcript as it completes so interrupted runs can be resumed.
- Does not guess speaker names. Speaker identification/diarization is a separate step.

Requirements
------------
Python 3.10+
pip install --upgrade openai
ffmpeg and ffprobe available on PATH

Authentication
--------------
The script automatically loads a .env file from the current working directory.
Use OPENAI_API_KEY (recommended) or OPEN_API_KEY.

You can also set OPENAI_API_KEY directly in the environment.

PowerShell:
    $env:OPENAI_API_KEY="sk-..."

Example
-------
python transcribe_zoom_recording.py "GMT20260924-004849_Recording.m4a"

Optional:
python transcribe_zoom_recording.py recording.m4a --model gpt-4o-transcribe --chunk-minutes 15
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from openai import OpenAI


DEFAULT_MODEL = "gpt-4o-transcribe"
DEFAULT_CHUNK_MINUTES = 15
DEFAULT_BITRATE = "48k"


def load_dotenv_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file without extra dependencies."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {"\"", "\'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def get_openai_api_key() -> Optional[str]:
    """Return the API key, supporting both standard and legacy/local names."""
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("OPEN_API_KEY")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def require_program(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(
            f"Required program '{name}' was not found on PATH.\n"
            f"Install FFmpeg and ensure both ffmpeg and ffprobe are available."
        )


def get_duration_seconds(audio_path: Path) -> float:
    result = run([
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ])
    return float(result.stdout.strip())


def hhmmss(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def make_chunk(
    source: Path,
    out_path: Path,
    start_seconds: float,
    duration_seconds: float,
    bitrate: str,
) -> None:
    # Mono, 16 kHz MP3 keeps chunks compact while remaining suitable for speech.
    run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-ss", str(start_seconds),
        "-t", str(duration_seconds),
        "-i", str(source),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", bitrate,
        str(out_path),
    ])


def load_existing_chunk_transcript(json_path: Path) -> Optional[str]:
    if not json_path.exists():
        return None
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        text = data.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    except Exception:
        pass
    return None


def save_chunk_transcript(
    json_path: Path,
    *,
    index: int,
    start: float,
    end: float,
    model: str,
    text: str,
) -> None:
    payload = {
        "chunk_index": index,
        "start_seconds": start,
        "end_seconds": end,
        "start_timestamp": hhmmss(start),
        "end_timestamp": hhmmss(end),
        "model": model,
        "text": text,
    }
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def transcribe_chunk(
    client: OpenAI,
    chunk_path: Path,
    model: str,
    language: Optional[str],
    context_prompt: Optional[str],
) -> str:
    kwargs = {
        "model": model,
        "file": chunk_path.open("rb"),
    }

    # These parameters are accepted by current OpenAI transcription models.
    # If a future model rejects one, retry without optional parameters.
    if language:
        kwargs["language"] = language
    if context_prompt:
        kwargs["prompt"] = context_prompt

    try:
        result = client.audio.transcriptions.create(**kwargs)
    except Exception as exc:
        # Retry without optional prompting in case the selected model does not
        # support all optional fields.
        if context_prompt:
            kwargs.pop("prompt", None)
            result = client.audio.transcriptions.create(**kwargs)
        else:
            raise exc

    if isinstance(result, str):
        return result.strip()

    text = getattr(result, "text", None)
    if text is None and isinstance(result, dict):
        text = result.get("text")

    if not text:
        raise RuntimeError(f"Transcription response contained no text: {result!r}")

    return str(text).strip()


def assemble_outputs(
    source: Path,
    chunks: list[dict],
    txt_path: Path,
    md_path: Path,
    model: str,
) -> None:
    txt_lines = []
    md_lines = [
        f"# Transcript — {source.name}",
        "",
        f"- Source: `{source.name}`",
        f"- Model: `{model}`",
        "- Timestamps mark the beginning of each processed audio chunk.",
        "- Speaker names are not inferred.",
        "",
    ]

    for c in chunks:
        stamp = f"[{hhmmss(c['start'])}–{hhmmss(c['end'])}]"
        text = c["text"].strip()

        txt_lines.extend([stamp, text, ""])
        md_lines.extend([f"## {stamp}", "", text, ""])

    txt_path.write_text("\n".join(txt_lines).rstrip() + "\n", encoding="utf-8")
    md_path.write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe a long Zoom recording using the OpenAI API."
    )
    parser.add_argument("audio", type=Path, help="Input audio/video recording")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI transcription model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--chunk-minutes",
        type=float,
        default=DEFAULT_CHUNK_MINUTES,
        help=f"Chunk length in minutes (default: {DEFAULT_CHUNK_MINUTES})",
    )
    parser.add_argument(
        "--bitrate",
        default=DEFAULT_BITRATE,
        help=f"MP3 bitrate for temporary chunks (default: {DEFAULT_BITRATE})",
    )
    parser.add_argument(
        "--language",
        default="en",
        help='Language hint, e.g. "en". Use "" to omit. Default: en',
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Directory for temporary chunks and resumable chunk transcripts",
    )
    parser.add_argument(
        "--keep-chunks",
        action="store_true",
        help="Keep temporary MP3 chunks after successful completion",
    )
    args = parser.parse_args()

    require_program("ffmpeg")
    require_program("ffprobe")

    source = args.audio.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"Input file does not exist: {source}")
    if args.chunk_minutes <= 0:
        raise SystemExit("--chunk-minutes must be greater than zero.")
    # Load .env from the directory where the command is being run.
    load_dotenv_file(Path.cwd() / ".env")

    api_key = get_openai_api_key()
    if not api_key:
        raise SystemExit(
            "No OpenAI API key was found.\n"
            "Set OPENAI_API_KEY (recommended) or OPEN_API_KEY either in the environment "
            "or in a .env file in the current working directory.\n"
            'Example .env entry: OPENAI_API_KEY="sk-..."'
        )

    # Normalize to the standard variable name used by the OpenAI SDK.
    os.environ["OPENAI_API_KEY"] = api_key

    work_dir = (
        args.work_dir.expanduser().resolve()
        if args.work_dir
        else source.parent / f"{source.stem}_transcription_work"
    )
    chunks_dir = work_dir / "audio_chunks"
    transcripts_dir = work_dir / "chunk_transcripts"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    txt_path = source.parent / f"{source.stem}_transcript.txt"
    md_path = source.parent / f"{source.stem}_transcript.md"

    duration = get_duration_seconds(source)
    chunk_seconds = args.chunk_minutes * 60.0
    total_chunks = int((duration + chunk_seconds - 1) // chunk_seconds)

    print(f"Source:   {source}")
    print(f"Duration: {hhmmss(duration)}")
    print(f"Model:    {args.model}")
    print(f"Chunks:   {total_chunks} x ~{args.chunk_minutes:g} minutes")
    print()

    client = OpenAI()
    completed: list[dict] = []
    previous_tail = ""

    for i in range(total_chunks):
        start = i * chunk_seconds
        end = min(duration, start + chunk_seconds)
        chunk_duration = end - start

        chunk_name = f"chunk_{i+1:03d}_{hhmmss(start).replace(':','-')}.mp3"
        chunk_path = chunks_dir / chunk_name
        json_path = transcripts_dir / f"chunk_{i+1:03d}.json"

        existing = load_existing_chunk_transcript(json_path)
        if existing:
            print(
                f"[{i+1:03d}/{total_chunks:03d}] "
                f"{hhmmss(start)}–{hhmmss(end)} already transcribed; reusing."
            )
            text = existing
        else:
            print(
                f"[{i+1:03d}/{total_chunks:03d}] "
                f"{hhmmss(start)}–{hhmmss(end)} preparing..."
            )

            if not chunk_path.exists():
                make_chunk(
                    source,
                    chunk_path,
                    start,
                    chunk_duration,
                    args.bitrate,
                )

            print(
                f"[{i+1:03d}/{total_chunks:03d}] "
                f"{hhmmss(start)}–{hhmmss(end)} transcribing..."
            )

            # A small tail from the previous chunk can help preserve names/terms
            # across chunk boundaries without materially biasing the transcript.
            context_prompt = previous_tail[-800:] if previous_tail else None

            text = transcribe_chunk(
                client,
                chunk_path,
                args.model,
                args.language or None,
                context_prompt,
            )

            save_chunk_transcript(
                json_path,
                index=i + 1,
                start=start,
                end=end,
                model=args.model,
                text=text,
            )

        completed.append({
            "index": i + 1,
            "start": start,
            "end": end,
            "text": text,
        })
        previous_tail = text

        # Rebuild outputs after every chunk. This guarantees useful partial
        # output if the process is interrupted.
        assemble_outputs(
            source,
            completed,
            txt_path,
            md_path,
            args.model,
        )

    if not args.keep_chunks:
        shutil.rmtree(chunks_dir, ignore_errors=True)

    print()
    print("Complete.")
    print(f"Text transcript:     {txt_path}")
    print(f"Markdown transcript: {md_path}")
    print(f"Resume metadata:     {transcripts_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
