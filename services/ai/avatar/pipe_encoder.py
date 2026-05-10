"""pipe_encoder — encode numpy BGR frames to MP4 via ffmpeg stdin pipe.

Avoids writing intermediate PNGs to disk: each frame's raw BGR24 bytes are
streamed directly into ffmpeg's stdin, saving the ~3-6 s of disk I/O that
the write-then-read-back pattern paid per render.

Public API
----------
encode_frames_to_mp4(frames, output_path, fps, audio_path, crf, use_nvenc)
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import numpy as np


def encode_frames_to_mp4(
    frames: list[np.ndarray],
    output_path: Path,
    fps: int = 25,
    audio_path: Optional[Path] = None,
    crf: int = 18,
    use_nvenc: bool = False,
) -> Path:
    """Encode BGR uint8 numpy frames to MP4 by piping raw video to ffmpeg stdin.

    Optionally muxes audio in the same ffmpeg invocation (no temp video file).
    Optionally uses h264_nvenc instead of libx264.

    Parameters
    ----------
    frames:
        List of BGR uint8 numpy arrays, all the same shape (H, W, 3).
    output_path:
        Destination MP4 path. Parent directory must already exist.
    fps:
        Output frame rate.
    audio_path:
        If provided, mux this audio file into the output MP4 with AAC.
        ``-shortest`` is used so the output duration matches whichever
        stream ends first.
    crf:
        Constant-Rate Factor for libx264, or roughly equivalent ``-cq``
        value for h264_nvenc. Lower = higher quality / larger file.
    use_nvenc:
        If True, use ``h264_nvenc -preset p4`` instead of
        ``libx264 -preset ultrafast``.

    Returns
    -------
    Path
        The ``output_path`` that was written.

    Raises
    ------
    ValueError
        If ``frames`` is empty or any frame has a different shape from the
        first frame.
    RuntimeError
        If ffmpeg exits with a non-zero return code, or if the output file
        is absent after ffmpeg reports success.
    """
    if not frames:
        raise ValueError("no frames to encode")

    ref_shape = frames[0].shape
    if len(ref_shape) != 3 or ref_shape[2] != 3:
        raise ValueError(
            f"frames[0] must be HxWx3 BGR; got shape {ref_shape}"
        )

    height, width = ref_shape[:2]

    for idx, frame in enumerate(frames[1:], start=1):
        if frame.shape != ref_shape:
            raise ValueError(
                f"frame {idx} shape {frame.shape} != reference shape {ref_shape}"
            )

    # Build ffmpeg command.
    # Input 0: raw BGR24 from stdin.
    video_input = [
        "-f", "rawvideo",
        "-pixel_format", "bgr24",
        "-video_size", f"{width}x{height}",
        "-framerate", str(fps),
        "-i", "pipe:0",
    ]

    # Optional audio input.
    audio_input: list[str] = []
    audio_output: list[str] = []
    if audio_path is not None:
        audio_input = ["-i", str(audio_path)]
        audio_output = ["-c:a", "aac", "-shortest"]

    # Video codec selection.
    if use_nvenc:
        video_codec = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", str(crf)]
    else:
        video_codec = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", str(crf)]

    cmd = (
        ["ffmpeg", "-y", "-v", "warning"]
        + video_input
        + audio_input
        + video_codec
        + ["-pix_fmt", "yuv420p"]
        + audio_output
        + [str(output_path)]
    )

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Stream raw frame bytes to ffmpeg stdin.
    assert proc.stdin is not None
    for frame in frames:
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()

    _, stderr_bytes = proc.communicate()
    rc = proc.returncode

    if rc != 0:
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"ffmpeg exited with code {rc}.\nCommand: {' '.join(cmd)}\n"
            f"stderr:\n{stderr_text}"
        )

    if not output_path.exists():
        raise RuntimeError(
            f"ffmpeg returned 0 but output file is missing: {output_path}"
        )

    return output_path
