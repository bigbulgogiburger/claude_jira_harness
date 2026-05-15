#!/usr/bin/env python3
"""
transcribe.py — audio file → transcript (with timestamps).

llm-wiki skill 의 source-types.md §3 (Podcast) / §7 (Voice memo) 에서 호출.

사용:
    python transcribe.py --audio <path> --output-dir <raw/audio/> --slug <slug>

산출:
    <output-dir>/<slug>.transcript.txt   # plain text with timestamps
    <output-dir>/<slug>.transcript.json  # segments (start/end/text/speaker?)
    <output-dir>/<slug>.meta.json        # duration, language, model_used

폴백 체인:
    1. OPENAI_API_KEY 있으면 OpenAI Whisper API (whisper-1)
       — 25MB 제한, 큰 파일은 ffmpeg 로 chunk 분할
    2. faster-whisper 로컬 모델 (CPU OK, GPU 가속 옵션)
    3. 모두 실패 시 stderr 에 메시지 + exit 1 — 사용자 paste 폴백
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

# ----- Helpers -----

def fmt_ts(seconds: float) -> str:
    """초 → [HH:MM:SS]."""
    td = timedelta(seconds=int(seconds))
    h, rem = divmod(td.seconds, 3600)
    m, s = divmod(rem, 60)
    return f"[{td.days * 24 + h:02d}:{m:02d}:{s:02d}]"


def probe_duration(audio_path: Path) -> float | None:
    """ffprobe 로 길이(초). 실패 시 None."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip()) if out.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return None


# ----- OpenAI Whisper API -----

def transcribe_openai(audio_path: Path, language: str | None = None) -> dict | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None

    client = OpenAI(api_key=api_key)
    size_mb = audio_path.stat().st_size / (1024 * 1024)

    if size_mb > 24.5:  # 25 MB API limit, 약간 여유
        return _transcribe_openai_chunked(client, audio_path, language)

    with audio_path.open("rb") as f:
        kwargs = {
            "model": "whisper-1",
            "file": f,
            "response_format": "verbose_json",
            "timestamp_granularities": ["segment"],
        }
        if language:
            kwargs["language"] = language
        result = client.audio.transcriptions.create(**kwargs)

    return _normalize_openai(result, model="whisper-1")


def _transcribe_openai_chunked(client, audio_path: Path, language: str | None) -> dict | None:
    """ffmpeg 로 10분 chunk 분할 후 각각 transcribe + 합치기."""
    if not _has_ffmpeg():
        print("WARN: large file but ffmpeg not found; OpenAI API skipped.", file=sys.stderr)
        return None

    duration = probe_duration(audio_path) or 0.0
    chunk_sec = 600  # 10 min
    n_chunks = int(duration // chunk_sec) + 1
    segments: list[dict] = []
    full_text: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        for i in range(n_chunks):
            start = i * chunk_sec
            chunk_path = Path(td) / f"chunk-{i:03d}.mp3"
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-ss", str(start),
                "-t", str(chunk_sec),
                "-i", str(audio_path),
                "-c:a", "libmp3lame", "-b:a", "64k",
                str(chunk_path),
            ]
            if subprocess.run(cmd, capture_output=True).returncode != 0:
                continue
            if not chunk_path.exists() or chunk_path.stat().st_size < 1000:
                continue

            with chunk_path.open("rb") as f:
                kwargs = {
                    "model": "whisper-1",
                    "file": f,
                    "response_format": "verbose_json",
                    "timestamp_granularities": ["segment"],
                }
                if language:
                    kwargs["language"] = language
                try:
                    chunk_result = client.audio.transcriptions.create(**kwargs)
                except Exception as e:
                    print(f"WARN: chunk {i} failed — {e}", file=sys.stderr)
                    continue

            cr = _normalize_openai(chunk_result, model="whisper-1")
            for seg in cr.get("segments", []):
                seg = dict(seg)
                seg["start"] += start
                seg["end"] += start
                segments.append(seg)
                full_text.append(seg["text"])

    return {
        "text": " ".join(full_text).strip(),
        "segments": segments,
        "model_used": "whisper-1 (chunked)",
        "language": language or "unknown",
    }


def _normalize_openai(result, model: str) -> dict:
    """OpenAI SDK response → 통일 형태."""
    if hasattr(result, "model_dump"):
        d = result.model_dump()
    elif hasattr(result, "to_dict"):
        d = result.to_dict()
    else:
        d = dict(result)
    return {
        "text": d.get("text", ""),
        "segments": [
            {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
            for s in d.get("segments", [])
        ],
        "language": d.get("language", "unknown"),
        "model_used": model,
    }


# ----- faster-whisper (local) -----

def transcribe_local(audio_path: Path, model_size: str = "base", language: str | None = None) -> dict | None:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        return None

    model = WhisperModel(model_size, device="auto", compute_type="auto")
    segments_gen, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
    )
    segments = [
        {"start": s.start, "end": s.end, "text": s.text.strip()}
        for s in segments_gen
    ]
    return {
        "text": " ".join(s["text"] for s in segments),
        "segments": segments,
        "language": info.language if hasattr(info, "language") else (language or "unknown"),
        "model_used": f"faster-whisper-{model_size}",
    }


def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ----- Output writers -----

def write_outputs(result: dict, out_dir: Path, slug: str, audio_path: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    txt_path = out_dir / f"{slug}.transcript.txt"
    lines = []
    for seg in result.get("segments", []):
        ts = fmt_ts(seg["start"])
        lines.append(f"{ts} {seg['text']}")
    txt_path.write_text("\n".join(lines) or result.get("text", ""), encoding="utf-8")

    json_path = out_dir / f"{slug}.transcript.json"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    meta = {
        "audio_path": str(audio_path),
        "duration_seconds": probe_duration(audio_path),
        "language": result.get("language"),
        "model_used": result.get("model_used"),
        "segment_count": len(result.get("segments", [])),
        "word_count": len(result.get("text", "").split()),
    }
    meta_path = out_dir / f"{slug}.meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


# ----- Main -----

def main():
    p = argparse.ArgumentParser(description="Transcribe audio → text + timestamps.")
    p.add_argument("--audio", required=True, help="입력 오디오 파일")
    p.add_argument("--output-dir", default=".", help="raw/audio/ 등")
    p.add_argument("--slug", required=True, help="파일명 베이스")
    p.add_argument("--language", default=None, help="ISO 639-1 (en/ko/ja…) — auto detect default")
    p.add_argument("--model", default="base", help="faster-whisper 모델 size (tiny/base/small/medium/large)")
    p.add_argument("--engine", default="auto", choices=["auto", "openai", "local"])
    args = p.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"ERROR: audio not found — {audio_path}", file=sys.stderr)
        sys.exit(1)

    result = None
    if args.engine in ("auto", "openai"):
        result = transcribe_openai(audio_path, args.language)
        if result:
            pass
        elif args.engine == "openai":
            print("ERROR: OpenAI engine requested but unavailable.", file=sys.stderr)
            sys.exit(2)

    if not result and args.engine in ("auto", "local"):
        print("INFO: trying faster-whisper local…", file=sys.stderr)
        result = transcribe_local(audio_path, args.model, args.language)

    if not result:
        print(
            "ERROR: no transcription engine available.\n"
            "  - OpenAI: set OPENAI_API_KEY and `pip install openai`\n"
            "  - Local:  `pip install faster-whisper`\n"
            "  - Fallback: paste an external transcript manually.",
            file=sys.stderr,
        )
        sys.exit(3)

    meta = write_outputs(result, Path(args.output_dir), args.slug, audio_path)
    print(
        f"OK: {Path(args.output_dir) / (args.slug + '.transcript.txt')} "
        f"({meta['segment_count']} segments, {meta['word_count']} words, "
        f"model={meta['model_used']})"
    )


if __name__ == "__main__":
    main()
