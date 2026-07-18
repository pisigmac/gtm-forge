"""Long-form video -> scored clips. Three stages:

1. Transcribe  — whisper.cpp CLI locally (default) or the OpenAI Whisper API.
2. Score       — the LLM grades transcript windows on hook strength,
                 standalone watchability, and information density.
3. Cut         — ffmpeg commands per approved clip.

Every stage is a pure function until execution, so `--dry-run` shows the full
plan (including exact ffmpeg commands) without touching the video.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from gtm_forge.config import VideoSettings
from gtm_forge.llm.base import Provider


@dataclass(slots=True)
class Segment:
    start_s: float
    end_s: float
    text: str


@dataclass(slots=True)
class ClipPlan:
    start_s: float
    end_s: float
    score: int
    hook: str
    output: str = ""


def parse_whisper_json(payload: str) -> list[Segment]:
    """Parse whisper.cpp `-oj` output into timed segments."""
    data = json.loads(payload)
    segments: list[Segment] = []
    for item in data.get("transcription", []):
        offsets = item.get("offsets", {})
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        segments.append(
            Segment(
                start_s=float(offsets.get("from", 0)) / 1000.0,
                end_s=float(offsets.get("to", 0)) / 1000.0,
                text=text,
            )
        )
    return segments


def extract_audio_command(src: Path, wav: Path, ffmpeg_bin: str) -> list[str]:
    """16kHz mono WAV — the format whisper.cpp expects."""
    return [ffmpeg_bin, "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(wav)]


def whisper_command(settings: VideoSettings, wav: Path, out_base: Path) -> list[str]:
    return [
        settings.whisper_bin,
        "-m",
        settings.whisper_model_path,
        "-f",
        str(wav),
        "-oj",
        "-of",
        str(out_base),
    ]


def chunk_segments(segments: list[Segment], window_s: int = 90) -> list[Segment]:
    """Merge tiny whisper segments into scoreable windows of ~window_s seconds."""
    windows: list[Segment] = []
    current: Segment | None = None
    for seg in segments:
        if current is None:
            current = Segment(seg.start_s, seg.end_s, seg.text)
            continue
        if seg.end_s - current.start_s <= window_s:
            current.end_s = seg.end_s
            current.text += " " + seg.text
        else:
            windows.append(current)
            current = Segment(seg.start_s, seg.end_s, seg.text)
    if current is not None:
        windows.append(current)
    return windows


_SCORER_SYSTEM = (
    "You are a short-form video editor. You will receive timestamped transcript windows "
    "from a long-form video. Pick the windows that work as STANDALONE clips: strong hook "
    "in the first seconds, a complete thought, dense information. "
    "Respond with ONLY valid JSON: a list of objects "
    '[{"start_s": <number>, "end_s": <number>, "score": <0-100>, "hook": "<first line>"}]. '
    "Order by score descending. Merge adjacent windows when the thought spans them."
)


def score_windows(
    provider: Provider,
    windows: list[Segment],
    *,
    clip_count: int,
    model: str,
    max_tokens: int = 2000,
    temperature: float = 0.2,
) -> list[ClipPlan]:
    listing = "\n".join(f"[{w.start_s:.1f} - {w.end_s:.1f}] {w.text}" for w in windows)
    result = provider.complete(
        system=_SCORER_SYSTEM,
        prompt=f"Transcript windows:\n{listing}\n\nReturn at most {clip_count} clips.",
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return parse_clip_plan(result.text)[:clip_count]


def parse_clip_plan(text: str) -> list[ClipPlan]:
    """Extract the JSON clip list from a model response."""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON list found in scorer response: {text[:200]!r}")
    raw = json.loads(text[start : end + 1])
    clips: list[ClipPlan] = []
    for item in raw:
        clips.append(
            ClipPlan(
                start_s=float(item["start_s"]),
                end_s=float(item["end_s"]),
                score=max(0, min(100, int(item.get("score", 0)))),
                hook=str(item.get("hook", ""))[:120],
            )
        )
    return sorted(clips, key=lambda c: c.score, reverse=True)


def build_cut_commands(src: Path, clips: list[ClipPlan], out_dir: Path, ffmpeg_bin: str) -> list[list[str]]:
    """One ffmpeg command per clip. Re-encodes for frame-accurate cuts."""
    commands: list[list[str]] = []
    for i, clip in enumerate(clips, start=1):
        out = out_dir / f"clip_{i:02d}_{int(clip.start_s)}s.mp4"
        clip.output = str(out)
        commands.append(
            [
                ffmpeg_bin,
                "-y",
                "-ss",
                f"{clip.start_s:.3f}",
                "-to",
                f"{clip.end_s:.3f}",
                "-i",
                str(src),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(out),
            ]
        )
    return commands


def run_commands(commands: list[list[str]]) -> list[str]:
    """Execute shell commands, returning the rendered command lines that ran."""
    ran: list[str] = []
    for cmd in commands:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        ran.append(shlex.join(cmd))
    return ran


def render_plan(commands: list[list[str]]) -> list[str]:
    """Human-readable command lines for dry-run output."""
    return [shlex.join(cmd) for cmd in commands]
