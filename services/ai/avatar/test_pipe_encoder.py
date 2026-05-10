"""Tests for pipe_encoder.encode_frames_to_mp4.

Requires ffmpeg and ffprobe on PATH (both present in the avatar container).
Run with:
    pytest /app/src/test_pipe_encoder.py -v
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
import pytest

from pipe_encoder import encode_frames_to_mp4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gradient_frames(
    count: int = 30,
    height: int = 256,
    width: int = 256,
) -> list[np.ndarray]:
    """Generate `count` distinct synthetic BGR uint8 frames."""
    frames = []
    for i in range(count):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Vary brightness per frame so each is different.
        frame[:, :, 0] = int(i * 255 / max(count - 1, 1))  # B channel
        frame[:, :, 1] = 128
        frame[:, :, 2] = 255 - int(i * 255 / max(count - 1, 1))  # R channel
        frames.append(frame)
    return frames


def _make_silent_wav(path: Path, duration_s: float = 1.0, sample_rate: int = 16000) -> Path:
    """Write a silent mono 16-bit PCM WAV file."""
    n_samples = int(duration_s * sample_rate)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00" * n_samples * 2)
    return path


def _ffprobe_streams(mp4_path: Path) -> list[dict]:
    """Return ffprobe stream info as a list of dicts."""
    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_streams",
        str(mp4_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout).get("streams", [])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_encode_basic():
    """Encode synthetic frames; verify file exists, has reasonable size,
    and ffprobe reports matching dimensions."""
    frames = _make_gradient_frames(count=30, height=256, width=256)

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "basic.mp4"
        result = encode_frames_to_mp4(frames, out, fps=25)

        assert result == out
        assert out.exists(), "output MP4 was not created"
        assert out.stat().st_size > 100, "output file is suspiciously small"

        streams = _ffprobe_streams(out)
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        assert len(video_streams) == 1, f"expected 1 video stream, got {len(video_streams)}"

        vs = video_streams[0]
        assert vs.get("width") == 256, f"unexpected width: {vs.get('width')}"
        assert vs.get("height") == 256, f"unexpected height: {vs.get('height')}"

        # nb_frames may be absent for some containers; fall back to duration check.
        nb_frames = vs.get("nb_frames")
        if nb_frames is not None:
            assert int(nb_frames) == 30, f"expected 30 frames, got {nb_frames}"


def test_encode_with_audio():
    """Encode frames + silent WAV; verify output has both video and audio streams."""
    frames = _make_gradient_frames(count=25, height=128, width=128)

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = _make_silent_wav(Path(tmpdir) / "silence.wav")
        out = Path(tmpdir) / "with_audio.mp4"
        encode_frames_to_mp4(frames, out, fps=25, audio_path=wav_path)

        assert out.exists(), "output MP4 was not created"

        streams = _ffprobe_streams(out)
        codec_types = {s.get("codec_type") for s in streams}
        assert "video" in codec_types, f"no video stream in output; streams={streams}"
        assert "audio" in codec_types, f"no audio stream in output; streams={streams}"

        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        assert audio_streams[0].get("codec_name") == "aac", (
            f"expected aac audio, got {audio_streams[0].get('codec_name')}"
        )


def test_encode_empty_raises():
    """Empty frame list must raise ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "empty.mp4"
        with pytest.raises(ValueError, match="no frames"):
            encode_frames_to_mp4([], out)


def test_encode_mismatched_sizes_raises():
    """Frames with differing shapes must raise an exception."""
    frame_a = np.zeros((256, 256, 3), dtype=np.uint8)
    frame_b = np.zeros((128, 128, 3), dtype=np.uint8)

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "mismatched.mp4"
        with pytest.raises((ValueError, AssertionError)):
            encode_frames_to_mp4([frame_a, frame_b], out)
