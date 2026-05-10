"""GPU-accelerated face blending for MuseTalk output frames.

Upstream reference (read 2026-05-10):
  /app/MuseTalk/musetalk/utils/blending.py  ->  get_image()
  /app/MuseTalk/musetalk/utils/face_parsing/__init__.py  ->  FaceParsing.__call__()

What the upstream does (get_image, verbatim logic):
  1. get_crop_box(face_box, expand=1.5) -> enlarged square crop around the face bbox.
  2. Crop that region from the body image ("face_large").
  3. Run FaceParsing on face_large (PIL Image -> BiSeNet on GPU -> PIL Image of labels).
  4. Keep only the face-bbox sub-region of the parsing output; paste it into a same-size
     black canvas (so the mask only covers the face, not the entire expanded crop).
  5. Zero-out the top `upper_boundary_ratio` (0.5) of that mask (only talking region).
  6. Gaussian-blur: kernel = int(0.05 * crop_w // 2 * 2) + 1  (same-parity as crop_w).
  7. Paste the predicted face into face_large at (x-x_s, y-y_s).
  8. Paste face_large back into body using the blurred mask as alpha.
  Returns BGR uint8.

FaceParsing.__call__ (face_parsing/__init__.py):
  - Accepts PIL.Image, resizes to 512x512 internally.
  - Runs BiSeNet on GPU (no-grad).
  - Returns PIL.Image of uint8 parsing labels (class IDs 0..18).
  - Mode "jaw": skin class [1] dilated+eroded+cheek-masked -> set to 255; lip classes
    [11,12,13] also set to 255; exclude class 10 (nose); all others -> 0.
  - Mode "neck": classes [1,11,12,13,14] -> 255, else 0.
  - Mode "raw":  classes [1,11,12,13]    -> 255, else 0.
  NOTE: FaceParsing does not accept torch tensors — it requires PIL.Image input.

GPU strategy:
  - Resize predicted crop: torch.nn.functional.interpolate (bilinear) on GPU.
    Quality difference vs cv2.resize(INTER_LINEAR): sub-pixel rounding may differ by
    <=1 LSB at boundaries; negligible for 8-bit video.
  - Gaussian-blur the mask: depthwise F.conv2d with a precomputed kernel, cached.
  - Alpha-composite body+face: vectorised tensor ops, no Python pixel loops.
  - FaceParsing itself still runs on GPU internally (BiSeNet), which is where most of
    the parsing time lived; we just avoid the extra CPU numpy round-trips in blending.
  Per-frame Python loop is intentional — varying bbox sizes make cross-frame batching
  awkward; the speedup is from eliminating numpy/PIL overhead inside get_image.
"""

from __future__ import annotations

import logging
import math
from functools import lru_cache
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

logger = logging.getLogger("avatar.gpu_blend")

# ---------------------------------------------------------------------------
# Gaussian kernel factory (cached by size/sigma/device)
# ---------------------------------------------------------------------------

def _device_key(d: torch.device) -> str:
    """Normalise a torch.device to a canonical string for use as a cache key.

    ``torch.device("cuda")`` and ``torch.device("cuda:0")`` are functionally
    identical on single-GPU but produce different ``str()`` representations.
    This helper maps both to ``"cuda:0"`` so the LRU cache hits correctly.
    """
    if d.type == "cuda":
        idx = d.index if d.index is not None else 0
        return f"cuda:{idx}"
    return d.type


@lru_cache(maxsize=32)
def _gauss_kernel(
    ksize: int,
    sigma: float,
    device_str: str,
) -> torch.Tensor:
    """Return a (1, 1, ksize, ksize) float32 Gaussian kernel on the given device."""
    ax = torch.arange(ksize, dtype=torch.float32) - ksize // 2
    g = torch.exp(-(ax ** 2) / (2 * sigma ** 2))
    g /= g.sum()
    kernel_2d = g[:, None] * g[None, :]  # (ksize, ksize)
    return kernel_2d.unsqueeze(0).unsqueeze(0).to(device_str)  # (1,1,ksize,ksize)


def _blur_mask_gpu(
    mask_np: np.ndarray,  # H x W, uint8 0/255
    ksize: int,
    device: torch.device,
) -> torch.Tensor:
    """Gaussian-blur a 2-D mask on GPU. Returns (H, W) float32 tensor in [0,1]."""
    if ksize < 1:
        ksize = 1
    # Make ksize odd (upstream uses int(x//2*2)+1 which is always odd)
    if ksize % 2 == 0:
        ksize += 1
    sigma = 0.3 * ((ksize - 1) * 0.5 - 1) + 0.8  # OpenCV default sigma
    kernel = _gauss_kernel(ksize, sigma, _device_key(device))

    t = torch.from_numpy(mask_np).to(device=device, dtype=torch.float32) / 255.0
    t = t.unsqueeze(0).unsqueeze(0)  # (1,1,H,W)
    pad = ksize // 2
    t_padded = F.pad(t, (pad, pad, pad, pad), mode="reflect")
    blurred = F.conv2d(t_padded, kernel)  # (1,1,H,W)
    return blurred.squeeze(0).squeeze(0)  # (H,W)


# ---------------------------------------------------------------------------
# Geometry helpers (mirrors blending.py: get_crop_box)
# ---------------------------------------------------------------------------

def _get_crop_box(
    x: int, y: int, x1: int, y1: int, expand: float = 1.5
) -> tuple[int, int, int, int]:
    """Replicate blending.py get_crop_box(expand=1.5) exactly."""
    x_c = (x + x1) // 2
    y_c = (y + y1) // 2
    w = x1 - x
    h = y1 - y
    s = int(max(w, h) // 2 * expand)
    return x_c - s, y_c - s, x_c + s, y_c + s


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def gpu_blend_batch(
    ori_frames: list[np.ndarray],
    res_frames: list[np.ndarray],
    bboxes: list[list[int]],
    face_parser,
    parsing_mode: str = "jaw",
    version: str = "v15",
    device: torch.device = torch.device("cuda"),
    upper_boundary_ratio: float = 0.5,
    expand: float = 1.5,
) -> list[np.ndarray]:
    """Blend predicted face crops back into source frames on GPU.

    Replicates musetalk.utils.blending.get_image() faithfully, replacing the
    CPU resize + numpy blending hot-path with GPU tensor ops.

    Args:
        ori_frames:    Source frames, BGR uint8, shape (H, W, 3). NOT mutated.
        res_frames:    Predicted face crops from VAE decode, BGR uint8 or float,
                       shape (crop_h, crop_w, 3).
        bboxes:        [x1, y1, x2, y2] per frame.  For v15 the caller must
                       already have applied extra_margin to y2 (matches worker.py).
        face_parser:   MuseTalk FaceParsing instance.
        parsing_mode:  "jaw" | "neck" | "raw" — forwarded to face_parser.
        version:       "v15" or other.  Passed through; bbox is caller's responsibility.
        device:        Torch device for GPU ops.
        upper_boundary_ratio: Fraction of crop height to zero-mask at top (0.5).
        expand:        Crop expansion factor matching get_crop_box (1.5).

    Returns:
        List of full-size BGR uint8 numpy frames, same shapes as ori_frames.
        Does NOT mutate ori_frames.
    """
    if not ori_frames:
        return []

    results: list[np.ndarray] = []

    for idx, (ori_frame, res_frame_raw, bbox) in enumerate(
        zip(ori_frames, res_frames, bboxes)
    ):
        x1, y1, x2, y2 = [int(v) for v in bbox]

        # Guard against degenerate bboxes
        if x2 <= x1 or y2 <= y1:
            logger.warning("Frame %d: degenerate bbox %s — skipping blend", idx, bbox)
            results.append(ori_frame.copy())
            continue

        target_w = x2 - x1
        target_h = y2 - y1

        # ------------------------------------------------------------------
        # 1. Resize predicted crop to bbox size on GPU
        # ------------------------------------------------------------------
        try:
            pred_uint8 = res_frame_raw.astype(np.uint8) if res_frame_raw.dtype != np.uint8 else res_frame_raw
            pred_t = (
                torch.from_numpy(pred_uint8)
                .to(device=device, dtype=torch.float32)
                .permute(2, 0, 1)
                .unsqueeze(0)  # (1, 3, h, w)
            )
            pred_resized = F.interpolate(
                pred_t,
                size=(target_h, target_w),
                mode="bilinear",
                align_corners=False,
            ).squeeze(0)  # (3, target_h, target_w)  float32
        except Exception:  # noqa: BLE001
            logger.exception("Frame %d: resize failed — skipping blend", idx)
            results.append(ori_frame.copy())
            continue

        # ------------------------------------------------------------------
        # 2. Build expanded crop box (mirrors get_crop_box in blending.py)
        # ------------------------------------------------------------------
        img_h, img_w = ori_frame.shape[:2]
        x_s, y_s, x_e, y_e = _get_crop_box(x1, y1, x2, y2, expand=expand)

        # Clamp to image bounds (PIL.Image.crop accepts out-of-bounds; we must too)
        # We'll track the unclamped coords for offset arithmetic, clamp for slicing.
        x_s_c = max(0, x_s)
        y_s_c = max(0, y_s)
        x_e_c = min(img_w, x_e)
        y_e_c = min(img_h, y_e)

        crop_w = x_e - x_s   # unclamped (matches PIL behaviour)
        crop_h = y_e - y_s

        if crop_w <= 0 or crop_h <= 0:
            logger.warning("Frame %d: crop box degenerate — skipping blend", idx)
            results.append(ori_frame.copy())
            continue

        # ------------------------------------------------------------------
        # 3. Extract face_large (expanded crop) as PIL Image for face parser
        #    Matches: face_large = body.crop(crop_box) in blending.py
        #    PIL.Image.crop pads with black for out-of-bounds regions.
        # ------------------------------------------------------------------
        # Build a padded version of ori_frame for the crop
        pad_top = max(0, -y_s)
        pad_bot = max(0, y_e - img_h)
        pad_left = max(0, -x_s)
        pad_right = max(0, x_e - img_w)

        if pad_top > 0 or pad_bot > 0 or pad_left > 0 or pad_right > 0:
            body_padded = cv2.copyMakeBorder(
                ori_frame, pad_top, pad_bot, pad_left, pad_right,
                cv2.BORDER_CONSTANT, value=0,
            )
        else:
            body_padded = ori_frame

        # Slice the expanded crop from (possibly padded) body
        sy = y_s + pad_top
        sx = x_s + pad_left
        face_large_bgr = body_padded[sy : sy + crop_h, sx : sx + crop_w]

        # Convert to PIL RGB for face_parser (it expects RGB PIL Image)
        face_large_pil = Image.fromarray(face_large_bgr[:, :, ::-1])  # BGR->RGB

        # ------------------------------------------------------------------
        # 4. Run FaceParsing (on GPU internally; returns PIL Image of labels)
        # ------------------------------------------------------------------
        try:
            seg_pil = face_parser(face_large_pil, mode=parsing_mode)
        except Exception:  # noqa: BLE001
            logger.exception("Frame %d: face_parser failed — skipping blend", idx)
            results.append(ori_frame.copy())
            continue

        if seg_pil is None:
            logger.warning("Frame %d: face_parser returned None — skipping blend", idx)
            results.append(ori_frame.copy())
            continue

        # Resize seg output to match face_large size (face_seg does this in-place)
        seg_pil = seg_pil.resize(face_large_pil.size)  # (crop_w, crop_h)
        seg_np = np.array(seg_pil)  # (crop_h, crop_w) uint8 label map

        # ------------------------------------------------------------------
        # 5. Build mask restricted to the face bbox sub-region
        #    Matches: mask_small = mask_image.crop(...); mask_image = black; paste
        # ------------------------------------------------------------------
        # Offset of the face bbox within the expanded crop
        fx_s = x1 - x_s   # can be negative if expand pushes x_s < 0 ... but
        fy_s = y1 - y_s   # in practice these are the (x-x_s, y-y_s) offsets
        fx_e = x2 - x_s
        fy_e = y2 - y_s

        # Clamp sub-region to the crop canvas
        fx_s_c = max(0, fx_s)
        fy_s_c = max(0, fy_s)
        fx_e_c = min(crop_w, fx_e)
        fy_e_c = min(crop_h, fy_e)

        # Extract the face sub-region mask
        mask_canvas = np.zeros((crop_h, crop_w), dtype=np.uint8)
        if fx_e_c > fx_s_c and fy_e_c > fy_s_c:
            mask_sub = seg_np[fy_s_c:fy_e_c, fx_s_c:fx_e_c].copy()
            # In the upstream the sub-region is taken at (x-x_s,y-y_s,x1-x_s,y1-y_s)
            # and pasted at the same offset — i.e. it's always the same region.
            # We replicate: paste mask_sub back into a black canvas at the same coords.
            dst_y0 = max(0, fy_s)
            dst_y1 = dst_y0 + (fy_e_c - fy_s_c)
            dst_x0 = max(0, fx_s)
            dst_x1 = dst_x0 + (fx_e_c - fx_s_c)
            # Guard for out-of-canvas pasting
            if dst_y1 <= crop_h and dst_x1 <= crop_w and dst_y1 > 0 and dst_x1 > 0:
                mask_canvas[dst_y0:dst_y1, dst_x0:dst_x1] = mask_sub

        # ------------------------------------------------------------------
        # 6. Zero-out top upper_boundary_ratio of the mask (talking region only)
        # ------------------------------------------------------------------
        top_boundary = int(crop_h * upper_boundary_ratio)
        mask_canvas[:top_boundary, :] = 0

        # ------------------------------------------------------------------
        # 7. Gaussian blur on GPU
        #    blur_kernel_size = int(0.05 * crop_w // 2 * 2) + 1
        # ------------------------------------------------------------------
        blur_ksize = int(0.05 * crop_w // 2 * 2) + 1
        mask_t = _blur_mask_gpu(mask_canvas, blur_ksize, device)  # (crop_h, crop_w) float32 [0,1]

        # ------------------------------------------------------------------
        # 8. Paste predicted face into face_large on GPU, then alpha-composite
        #    into body tensor.
        #
        #    Upstream PIL logic:
        #      face_large.paste(face, (x-x_s, y-y_s, x1-x_s, y1-y_s))
        #      body.paste(face_large, crop_box[:2], mask_image)
        #
        #    face_large is the expanded crop; after pasting face into it, we
        #    alpha-composite the modified face_large region into body using mask_t.
        # ------------------------------------------------------------------
        # Work entirely on GPU tensors.
        # body_t: (3, img_h, img_w) float32
        body_t = (
            torch.from_numpy(ori_frame.copy())
            .to(device=device, dtype=torch.float32)
            .permute(2, 0, 1)
        )

        # face_large_t: (3, crop_h, crop_w) float32
        face_large_t = (
            torch.from_numpy(face_large_bgr.copy())
            .to(device=device, dtype=torch.float32)
            .permute(2, 0, 1)
        )

        # Paste predicted face into face_large_t at the face bbox offset
        paste_y0 = max(0, fy_s)
        paste_y1 = paste_y0 + target_h
        paste_x0 = max(0, fx_s)
        paste_x1 = paste_x0 + target_w

        # Clamp to crop canvas
        py0 = max(0, paste_y0)
        py1 = min(crop_h, paste_y1)
        px0 = max(0, paste_x0)
        px1 = min(crop_w, paste_x1)

        # Corresponding slice in the pred tensor
        pred_py0 = py0 - paste_y0
        pred_py1 = pred_py0 + (py1 - py0)
        pred_px0 = px0 - paste_x0
        pred_px1 = pred_px0 + (px1 - px0)

        if py1 > py0 and px1 > px0 and pred_py1 > pred_py0 and pred_px1 > pred_px0:
            face_large_t[:, py0:py1, px0:px1] = pred_resized[
                :, pred_py0:pred_py1, pred_px0:pred_px1
            ]

        # Alpha-composite face_large_t into body_t over the crop region.
        # mask_t: (crop_h, crop_w) float32 [0,1] -- broadcast to (3, crop_h, crop_w)
        m = mask_t.unsqueeze(0)  # (1, crop_h, crop_w)

        # Clamp the body-write region
        bdy0 = max(0, y_s)
        bdy1 = min(img_h, y_e)
        bdx0 = max(0, x_s)
        bdx1 = min(img_w, x_e)

        # Corresponding sub-region in crop tensors (for padded regions)
        cy0 = bdy0 - y_s
        cy1 = cy0 + (bdy1 - bdy0)
        cx0 = bdx0 - x_s
        cx1 = cx0 + (bdx1 - bdx0)

        if bdy1 > bdy0 and bdx1 > bdx0 and cy1 > cy0 and cx1 > cx0:
            body_region = body_t[:, bdy0:bdy1, bdx0:bdx1]      # (3, rh, rw)
            face_region = face_large_t[:, cy0:cy1, cx0:cx1]    # (3, rh, rw)
            mask_region = m[:, cy0:cy1, cx0:cx1]               # (1, rh, rw)
            blended = face_region * mask_region + body_region * (1.0 - mask_region)
            body_t[:, bdy0:bdy1, bdx0:bdx1] = blended

        # ------------------------------------------------------------------
        # 9. Convert back to BGR uint8 numpy
        # ------------------------------------------------------------------
        out_np = (
            body_t.clamp(0, 255)
            .byte()
            .permute(1, 2, 0)
            .cpu()
            .numpy()
        )  # (H, W, 3) BGR uint8

        results.append(out_np)

    return results
