"""Tests for gpu_blend.gpu_blend_batch.

Run with:
    pytest /app/src/test_gpu_blend.py -v

The test marked @pytest.mark.requires_musetalk imports from MuseTalk directly
and is skipped on machines where the MuseTalk package is not available.
"""

from __future__ import annotations

import importlib
import sys
from typing import Optional

import numpy as np
import pytest
import torch
from PIL import Image

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------
from gpu_blend import gpu_blend_batch

# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _solid_frame(h: int, w: int, color: tuple) -> np.ndarray:
    """Return a solid-colour BGR uint8 frame."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :] = color  # (B, G, R)
    return frame


def _random_frame(h: int, w: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, (h, w, 3), dtype=np.uint8)


class FakeFaceParser:
    """Synthetic face parser that returns a PIL Image of label 1 (skin) in the
    central region.  Class 1 is the skin class used by all three modes ("jaw",
    "neck", "raw") in MuseTalk's FaceParsing.  We additionally include class 11
    (upper lip) in a small strip near the bottom so mode="raw" also produces a
    non-trivial mask.
    """

    def __call__(
        self, image: Image.Image, size: tuple = (512, 512), mode: str = "raw"
    ) -> Image.Image:
        w, h = image.size
        labels = np.zeros((h, w), dtype=np.uint8)
        # Centre 50% = skin (class 1)
        y0 = h // 4
        y1 = 3 * h // 4
        x0 = w // 4
        x1 = 3 * w // 4
        labels[y0:y1, x0:x1] = 1
        # Bottom strip = upper lip (class 11)
        labels[int(0.75 * h) :, x0:x1] = 11
        return Image.fromarray(labels)


class AlwaysNoneFaceParser:
    """Parser that always returns None (simulates detection failure)."""

    def __call__(self, image: Image.Image, **kwargs) -> None:
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_inputs():
    """Three 480×640 source frames with 80×80 face bboxes."""
    h, w = 480, 640
    frames = [_random_frame(h, w, seed=i) for i in range(3)]
    bboxes = [
        [100, 120, 180, 200],  # 80×80
        [200, 150, 280, 230],  # 80×80
        [310, 200, 390, 280],  # 80×80
    ]
    crops = [_random_frame(80, 80, seed=10 + i) for i in range(3)]
    return frames, bboxes, crops


# ---------------------------------------------------------------------------
# Test 1 — Shape preservation
# ---------------------------------------------------------------------------

def test_output_shapes_match_input(small_inputs):
    ori_frames, bboxes, crops = small_inputs
    parser = FakeFaceParser()
    results = gpu_blend_batch(
        ori_frames, crops, bboxes, face_parser=parser, device=DEVICE
    )
    assert len(results) == len(ori_frames)
    for out, ori in zip(results, ori_frames):
        assert out.shape == ori.shape, f"Shape mismatch: {out.shape} vs {ori.shape}"
        assert out.dtype == np.uint8


# ---------------------------------------------------------------------------
# Test 2 — No input mutation
# ---------------------------------------------------------------------------

def test_no_input_mutation(small_inputs):
    ori_frames, bboxes, crops = small_inputs
    # Deep copy originals before call
    originals = [f.copy() for f in ori_frames]
    parser = FakeFaceParser()
    gpu_blend_batch(ori_frames, crops, bboxes, face_parser=parser, device=DEVICE)
    for before, after in zip(originals, ori_frames):
        np.testing.assert_array_equal(before, after, err_msg="ori_frames was mutated")


# ---------------------------------------------------------------------------
# Test 3 — Empty input
# ---------------------------------------------------------------------------

def test_empty_input():
    parser = FakeFaceParser()
    results = gpu_blend_batch([], [], [], face_parser=parser, device=DEVICE)
    assert results == []


# ---------------------------------------------------------------------------
# Test 4 — Mask is non-trivial (transition inside bbox region)
# ---------------------------------------------------------------------------

def test_mask_nontrivial_transition():
    """
    Use a solid blue source frame and a solid red predicted crop.
    If the mask is all-0 the output would be identical to source (all blue).
    If the mask is all-1 the output would be all red in the bbox.
    A non-trivial mask means the bbox region contains BOTH source and predicted
    pixels, i.e. neither extreme.
    """
    h, w = 480, 640
    # Bright blue source
    source = _solid_frame(h, w, color=(255, 0, 0))  # B=255, G=0, R=0
    # Bright red predicted crop — same size as bbox
    bbox = [100, 120, 180, 200]  # x1,y1,x2,y2 -> 80×80
    crop_h = bbox[3] - bbox[1]
    crop_w = bbox[2] - bbox[0]
    predicted = _solid_frame(crop_h, crop_w, color=(0, 0, 255))  # R=255, G=0, B=0

    parser = FakeFaceParser()
    results = gpu_blend_batch(
        [source], [predicted], [bbox], face_parser=parser, device=DEVICE,
        upper_boundary_ratio=0.3,   # lower boundary so mask is present in lower half
    )
    assert len(results) == 1
    out = results[0]

    # Extract the bbox region of the output
    x1, y1, x2, y2 = bbox
    roi = out[y1:y2, x1:x2]

    # The ROI should contain both "blue" and "non-blue" (red-blended) pixels.
    # Check that the B channel has values that are neither all 255 nor all 0.
    b_channel = roi[:, :, 0].astype(np.float32)
    assert b_channel.min() < 255, "Mask appears to be all-zero (no blending occurred)"
    assert b_channel.max() > 0, "Mask appears to be all-one (source fully replaced)"


# ---------------------------------------------------------------------------
# Test 5 — Zero-area bbox returns unmodified copy
# ---------------------------------------------------------------------------

def test_degenerate_bbox_skipped():
    h, w = 200, 200
    source = _random_frame(h, w)
    crop = _random_frame(10, 10)
    bbox_zero_w = [50, 50, 50, 100]  # x2==x1 -> zero width
    bbox_zero_h = [50, 50, 100, 50]  # y2==y1 -> zero height

    parser = FakeFaceParser()
    for bad_bbox in (bbox_zero_w, bbox_zero_h):
        results = gpu_blend_batch(
            [source], [crop], [bad_bbox], face_parser=parser, device=DEVICE
        )
        assert len(results) == 1
        np.testing.assert_array_equal(
            results[0], source, err_msg="Degenerate bbox should return ori_frame copy"
        )


# ---------------------------------------------------------------------------
# Test 6 — face_parser returning None is handled gracefully
# ---------------------------------------------------------------------------

def test_none_parser_returns_ori_copy():
    h, w = 200, 200
    source = _random_frame(h, w)
    crop = _random_frame(60, 60)
    bbox = [50, 50, 110, 110]

    parser = AlwaysNoneFaceParser()
    results = gpu_blend_batch(
        [source], [crop], [bbox], face_parser=parser, device=DEVICE
    )
    assert len(results) == 1
    np.testing.assert_array_equal(results[0], source)


# ---------------------------------------------------------------------------
# Test 7 — CPU vs GPU output comparison (gold-standard)
# ---------------------------------------------------------------------------

requires_musetalk = pytest.mark.skipif(
    importlib.util.find_spec("musetalk") is None,
    reason="musetalk package not available",
)


@requires_musetalk
def test_cpu_gpu_parity():
    """
    Compare gpu_blend_batch output against MuseTalk's reference get_image().
    Mean per-pixel L1 difference must be < 5/255 (i.e. < 5 on 0-255 scale).
    """
    import os
    from musetalk.utils.blending import get_image
    from musetalk.utils.face_parsing import FaceParsing

    # FaceParsing.__init__ resolves model weights relative to CWD.
    # The worker always chdir()s to /app/MuseTalk before constructing it.
    # Replicate that here so the test is self-contained.
    musetalk_dir = "/app/MuseTalk"
    old_cwd = os.getcwd()
    os.chdir(musetalk_dir)
    try:
        fp = FaceParsing()
    finally:
        os.chdir(old_cwd)

    # Small synthetic input to keep test fast
    h, w = 320, 240
    rng = np.random.default_rng(42)
    ori_frame = rng.integers(64, 192, (h, w, 3), dtype=np.uint8)
    bbox = [60, 70, 160, 170]  # 100×100
    x1, y1, x2, y2 = bbox
    # Create a predicted crop that is obviously different from source
    res_frame = rng.integers(0, 256, (y2 - y1, x2 - x1, 3), dtype=np.uint8)

    # --- CPU reference ---
    # Worker applies extra_margin before calling get_image (v15 path):
    extra_margin = 10
    y2_adj = min(y2 + extra_margin, h)
    res_resized_cpu = cv2.resize(res_frame.astype(np.uint8), (x2 - x1, y2_adj - y1))
    cpu_out = get_image(ori_frame, res_resized_cpu, [x1, y1, x2, y2_adj], fp=fp, mode="jaw")

    # --- GPU version ---
    # Same extra_margin adjustment already done; pass adjusted bbox
    gpu_results = gpu_blend_batch(
        [ori_frame.copy()],
        [res_frame.copy()],
        [[x1, y1, x2, y2_adj]],   # y2 already adjusted, matching worker.py
        face_parser=fp,
        parsing_mode="jaw",
        version="v15",
        device=DEVICE,
    )
    gpu_out = gpu_results[0]

    assert cpu_out.shape == gpu_out.shape, f"{cpu_out.shape} vs {gpu_out.shape}"

    diff = np.abs(cpu_out.astype(int) - gpu_out.astype(int))
    mean_diff = float(diff.mean())
    max_diff = int(diff.max())

    print(f"\nCPU vs GPU blend: mean_abs_diff={mean_diff:.4f}, max_diff={max_diff}")
    assert mean_diff < 2.0, (
        f"CPU/GPU blending diverged too much: mean_abs_diff={mean_diff:.4f} (threshold 2.0). "
        "Check mask geometry and Gaussian kernel."
    )
    assert max_diff < 15, (
        f"CPU/GPU blending L∞ diverged too much: max_diff={max_diff} (threshold 15). "
        "Check mask geometry and Gaussian kernel."
    )
