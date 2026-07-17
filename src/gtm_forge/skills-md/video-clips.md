---
name: gtm-video-clips
description: Turn long-form video (podcasts, webinars) into scored standalone clips using whisper.cpp transcription, LLM hook scoring, and ffmpeg cutting. Use when repurposing long video into shorts.
---

# Video Clips

## When to use
The user has a long video file and wants 3-5 upload-ready clips.

## Requirements
- ffmpeg and a whisper.cpp binary (whisper-cli) on PATH, plus a whisper model file.
- Configure paths under `video:` in config.yaml.

## Commands
```bash
gtm --dry-run video clips --src episode.mp4         # shows exact ffmpeg/whisper commands
gtm video clips --src episode.mp4 --count 4 [--out clips/]
```

## Rules
- Always dry-run first on a new machine to verify the toolchain.
- Output: clip files + manifest.json with start/end/score/hook per clip.
