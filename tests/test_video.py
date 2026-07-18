"""Video pipeline: parsing, chunking, clip plans, ffmpeg command building."""

from pathlib import Path

from gtm_forge.config import VideoSettings
from gtm_forge.skills.video.pipeline import (
    ClipPlan,
    Segment,
    build_cut_commands,
    chunk_segments,
    extract_audio_command,
    parse_clip_plan,
    parse_whisper_json,
    whisper_command,
)

WHISPER_JSON = (
    '{"transcription": ['
    '{"offsets": {"from": 0, "to": 5000}, "text": " Hello world"},'
    '{"offsets": {"from": 5000, "to": 12000}, "text": " Second part"},'
    '{"offsets": {"from": 12000, "to": 20000}, "text": ""}]}'
)


def test_parse_whisper_json():
    segments = parse_whisper_json(WHISPER_JSON)
    assert len(segments) == 2  # empty text skipped
    assert segments[0].start_s == 0.0
    assert segments[1].end_s == 12.0


def test_chunk_segments_merges_within_window():
    segments = [Segment(float(i * 10), float(i * 10 + 9), f"part {i}") for i in range(10)]
    windows = chunk_segments(segments, window_s=30)
    assert len(windows) > 1
    assert all(w.end_s - w.start_s <= 40 for w in windows)
    # total text preserved
    assert "part 0" in windows[0].text


def test_parse_clip_plan():
    text = (
        'Here you go:\n[{"start_s": 10, "end_s": 70, "score": 92, "hook": "Big claim"},'
        ' {"start_s": 100, "end_s": 160, "score": 85, "hook": "Second"}]'
    )
    clips = parse_clip_plan(text)
    assert len(clips) == 2
    assert clips[0].score == 92  # sorted by score desc


def test_build_cut_commands():
    clips = [ClipPlan(start_s=10.0, end_s=70.0, score=90, hook="h")]
    commands = build_cut_commands(Path("in.mp4"), clips, Path("/out"), "ffmpeg")
    assert len(commands) == 1
    cmd = commands[0]
    assert cmd[0] == "ffmpeg"
    assert "-ss" in cmd and "10.000" in cmd
    assert "libx264" in cmd
    assert clips[0].output.startswith("/out/clip_01")


def test_audio_and_whisper_commands():
    settings = VideoSettings()
    audio = extract_audio_command(Path("v.mp4"), Path("a.wav"), "ffmpeg")
    assert "16000" in audio
    whisper = whisper_command(settings, Path("a.wav"), Path("out"))
    assert "-oj" in whisper
