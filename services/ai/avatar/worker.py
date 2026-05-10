"""Persistent MuseTalk inference worker.

This module owns the heavy MuseTalk model state (UNet, VAE, positional
encoding, Whisper, FaceParsing) and exposes a single `infer()` call that
runs one job end-to-end. By keeping the models resident in GPU memory we
eliminate the ~60–90 s subprocess-per-request cost the avatar service
paid in Path 4 Phase 1.

Pipeline (mirrors `MuseTalk/scripts/inference.py`):

    1. (heavy, once) load_all_model -> vae, unet, pe
    2. (heavy, once) WhisperModel + AudioProcessor + FaceParsing
    3. (per request) extract source frames via ffmpeg
    4. (per request) get_audio_feature -> get_whisper_chunk
    5. (per request) get_landmark_and_bbox -> coord_list, frame_list
    6. (per request) vae.get_latents_for_unet for each crop
    7. (per request) batched UNet forward + vae.decode_latents
    8. (per request) blend predictions back into source frames
    9. (per request) pipe_encoder: stream frames to ffmpeg stdin, mux audio

The Phase 3 streaming path will reuse the loaded models from this same
class (see `infer_streaming` placeholder).

NOTE: this module imports from the MuseTalk repo cloned at build time at
`/app/MuseTalk` (added to PYTHONPATH by the Dockerfile). It intentionally
does *not* import torch/musetalk at module top level so unit tests on
machines without a GPU can still load the FastAPI shim.
"""

from __future__ import annotations

import glob
import hashlib
import logging
import os
import threading
from pathlib import Path
from typing import Optional

from pipe_encoder import encode_frames_to_mp4

logger = logging.getLogger("avatar.worker")


def _is_video(path: Path) -> bool:
    return path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


class MuseTalkWorker:
    """Owns the loaded MuseTalk model state. One instance per process.

    The class is *not* asyncio-aware on purpose — `infer()` is a blocking
    sync method. Run it from a thread (e.g. via `loop.run_in_executor`)
    or from the queue runner in `app.py`.
    """

    def __init__(
        self,
        unet_model_path: Path,
        unet_config: Path,
        whisper_dir: Path,
        version: str = "v15",
        vae_type: str = "sd-vae",
        device: str = "cuda",
        use_float16: bool = True,
        left_cheek_width: int = 90,
        right_cheek_width: int = 90,
    ) -> None:
        # Local imports — see module docstring.
        import torch
        from musetalk.utils.utils import load_all_model
        from musetalk.utils.audio_processor import AudioProcessor
        from musetalk.utils.face_parsing import FaceParsing
        from transformers import WhisperModel

        self.version = version
        self.use_float16 = use_float16
        self._torch_device = torch.device(device if torch.cuda.is_available() else "cpu")
        self._device_str = str(self._torch_device)

        logger.info(
            "loading MuseTalk weights: version=%s device=%s fp16=%s",
            version, self._device_str, use_float16,
        )

        # Heavy load #1: VAE + UNet + PE
        vae, unet, pe = load_all_model(
            unet_model_path=str(unet_model_path),
            vae_type=vae_type,
            unet_config=str(unet_config),
            device=self._torch_device,
        )
        if use_float16:
            pe = pe.half()
            vae.vae = vae.vae.half()
            unet.model = unet.model.half()
        pe = pe.to(self._torch_device)
        vae.vae = vae.vae.to(self._torch_device)
        unet.model = unet.model.to(self._torch_device)
        self.vae = vae
        self.unet = unet
        self.pe = pe
        self._timesteps = torch.tensor([0], device=self._torch_device)
        self._weight_dtype = unet.model.dtype

        # ---- torch.compile UNet + VAE decoder for 2-4x inference speedup ----
        # Controlled by env vars so this can be toggled without code changes.
        compile_enabled = os.environ.get("MUSETALK_COMPILE", "1") not in {"0", "false", "False", ""}
        compile_backend = os.environ.get("MUSETALK_COMPILE_BACKEND", "inductor")

        if compile_enabled:
            from trt_compile import try_compile, warmup_compiled_model  # noqa: F401

            self.unet.model = try_compile(
                self.unet.model, label="unet", backend=compile_backend,
            )
            self.vae.vae.decoder = try_compile(
                self.vae.vae.decoder, label="vae_decoder", backend=compile_backend,
            )

            # Warm up so the first real request doesn't pay the JIT cost.
            try:
                self._warmup_compiled_models()
            except Exception:  # noqa: BLE001
                logger.exception("warmup failed; first request may be slow")

        # Heavy load #2: Whisper + audio processor.
        self.audio_processor = AudioProcessor(feature_extractor_path=str(whisper_dir))
        whisper = WhisperModel.from_pretrained(str(whisper_dir))
        whisper = whisper.to(device=self._torch_device, dtype=self._weight_dtype).eval()
        whisper.requires_grad_(False)
        self.whisper = whisper

        # Heavy load #3: face parser. v15 takes cheek-width tuning.
        if version == "v15":
            self.face_parser = FaceParsing(
                left_cheek_width=left_cheek_width,
                right_cheek_width=right_cheek_width,
            )
        else:
            self.face_parser = FaceParsing()

        # Inference is single-threaded by design (one GPU). A re-entrant lock
        # protects the GPU pipeline from concurrent submissions.
        self._lock = threading.Lock()

        # Cache: source-video path -> (coord_list, frame_list, latent_list).
        # Idle-loop MP4s recur across many requests, so caching the
        # landmark/bbox/VAE-latent extraction is the biggest steady-state win.
        self._source_cache: dict[str, tuple[list, list, list]] = {}
        self._source_cache_max = 8

        logger.info("MuseTalkWorker ready (dtype=%s)", self._weight_dtype)

    # ------------------------------------------------------------------ utils

    def _extract_source(
        self,
        source_path: Path,
        workdir: Path,
        bbox_shift: int,
        extra_margin: int,
        fps_fallback: int,
    ) -> tuple[list, list, list, int]:
        """Pull frames + bboxes + VAE latents for the source.

        Cached by source_path string when the file looks immutable (size+mtime
        match). Persona idle-loops change rarely so this cache pays off.
        """
        from musetalk.utils.preprocessing import (
            coord_placeholder, get_landmark_and_bbox, read_imgs,
        )
        from musetalk.utils.utils import get_file_type, get_video_fps
        import cv2

        # Cache by *content* hash, not path: the avatar service receives
        # uploads into a fresh tempdir per request, so the path changes every
        # time even when the persona's idle-loop MP4 is byte-identical.
        # Content hash + size keys hit across all those copies and is the
        # whole point of the cache (re-extracting landmarks for 550 frames
        # is ~50 s on a 4090).
        cache_key = None
        try:
            stat = source_path.stat()
            h = hashlib.blake2b(digest_size=16)
            with open(source_path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            cache_key = f"{h.hexdigest()}|{stat.st_size}|{bbox_shift}|{extra_margin}|{self.version}"
        except OSError:
            pass

        if cache_key and cache_key in self._source_cache:
            coord_list, frame_list, input_latent_list, fps = self._source_cache[cache_key]
            return coord_list, frame_list, input_latent_list, fps

        ftype = get_file_type(str(source_path))
        if ftype == "video":
            frames_dir = workdir / "src_frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            cmd = (
                f'ffmpeg -v fatal -i "{source_path}" -start_number 0 '
                f'"{frames_dir}/%08d.png"'
            )
            rc = os.system(cmd)
            if rc != 0:
                raise RuntimeError(f"ffmpeg frame-extract failed (rc={rc}) for {source_path}")
            input_img_list = sorted(
                glob.glob(str(frames_dir / "*.[jpJP][pnPN]*[gG]"))
            )
            fps = get_video_fps(str(source_path))
        elif ftype == "image":
            input_img_list = [str(source_path)]
            fps = fps_fallback
        else:
            raise ValueError(f"unsupported source type for {source_path}")

        coord_list, frame_list = get_landmark_and_bbox(input_img_list, bbox_shift)

        input_latent_list: list = []
        for bbox, frame in zip(coord_list, frame_list):
            if bbox == coord_placeholder:
                continue
            x1, y1, x2, y2 = bbox
            if self.version == "v15":
                y2 = min(y2 + extra_margin, frame.shape[0])
            crop_frame = frame[y1:y2, x1:x2]
            crop_frame = cv2.resize(crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4)
            latents = self.vae.get_latents_for_unet(crop_frame)
            input_latent_list.append(latents)

        if cache_key:
            if len(self._source_cache) >= self._source_cache_max:
                # Drop oldest. dict preserves insertion order in 3.7+.
                self._source_cache.pop(next(iter(self._source_cache)))
            self._source_cache[cache_key] = (coord_list, frame_list, input_latent_list, fps)

        return coord_list, frame_list, input_latent_list, fps

    # ---------------------------------------------------------------- public

    def _warmup_compiled_models(self) -> None:
        """Trigger torch.compile JIT for UNet and VAE so first request is fast.

        Warmup shapes verified against a real render on 2026-05-10:
          - latent_batch:       (8, 8, 32, 32)   UNet in_channels=8, spatial=32x32
          - audio_feature_batch (8, 50, 384)      Whisper-tiny hidden dim=384, seq=50
          - pred_latents:       (8, 4, 32, 32)    UNet out_channels=4
          - vae decoder input:  (8, 4, 32, 32)    scaled pred_latents

        If warmup shapes diverge from real shapes, torch.compile will re-JIT
        on the first real request (first request slow, subsequent fast).
        """
        import torch
        from trt_compile import warmup_compiled_model

        warmup_batch = 8  # match default batch_size in infer()
        dummy_latent = torch.randn(
            warmup_batch, 8, 32, 32,
            device=self._torch_device, dtype=self._weight_dtype,
        )
        dummy_hidden = torch.randn(
            warmup_batch, 50, 384,
            device=self._torch_device, dtype=self._weight_dtype,
        )
        # PE wraps audio_features inside infer(); skip PE in warmup.
        # UNet call: model(latent, timesteps, encoder_hidden_states=hidden)
        # torch.compile traces positional-style, so pass hidden as positional
        # kwarg via a wrapper-free call matching the real call site.
        warmup_compiled_model(
            self.unet.model,
            (dummy_latent, self._timesteps, dummy_hidden),
            "unet",
        )
        # VAE decoder takes (B, 4, 32, 32) latents.
        dummy_vae_latent = torch.randn(
            warmup_batch, 4, 32, 32,
            device=self._torch_device, dtype=self._weight_dtype,
        )
        warmup_compiled_model(self.vae.vae.decoder, (dummy_vae_latent,), "vae_decoder")

    def preload_source(self, source_path: Path, bbox_shift: int = 0, extra_margin: int = 10) -> None:
        """Warm the source-frame / bbox / latent cache for a known idle-loop.

        Called from app startup for personas with `idle_video_url` so the
        first session for that persona doesn't pay the landmark-extraction
        cost. Safe to call repeatedly — the cache is keyed by file mtime.
        """
        try:
            with self._lock:
                self._extract_source(
                    source_path, source_path.parent, bbox_shift, extra_margin, fps_fallback=25,
                )
            logger.info("preloaded source: %s", source_path)
        except Exception:  # noqa: BLE001
            logger.exception("preload_source failed for %s", source_path)

    def infer(
        self,
        audio_path: Path,
        source_path: Path,
        output_dir: Path,
        bbox_shift: int = 0,
        extra_margin: int = 10,
        batch_size: int = 8,
        audio_padding_left: int = 2,
        audio_padding_right: int = 2,
        parsing_mode: str = "jaw",
        fps_fallback: int = 25,
        result_name: Optional[str] = None,
    ) -> Path:
        """Run one render. Blocking. Thread-safe (serialised by a lock)."""

        import numpy as np
        import torch
        from musetalk.utils.utils import datagen

        from gpu_blend import gpu_blend_batch

        output_dir.mkdir(parents=True, exist_ok=True)

        with self._lock, torch.no_grad():
            coord_list, frame_list, input_latent_list, fps = self._extract_source(
                source_path, output_dir, bbox_shift, extra_margin, fps_fallback,
            )

            whisper_input_features, librosa_length = self.audio_processor.get_audio_feature(
                str(audio_path),
            )
            whisper_chunks = self.audio_processor.get_whisper_chunk(
                whisper_input_features,
                self._torch_device,
                self._weight_dtype,
                self.whisper,
                librosa_length,
                fps=fps,
                audio_padding_length_left=audio_padding_left,
                audio_padding_length_right=audio_padding_right,
            )

            # Cycle frames so audio longer than the source loops gracefully.
            frame_list_cycle = frame_list + frame_list[::-1]
            coord_list_cycle = coord_list + coord_list[::-1]
            input_latent_list_cycle = input_latent_list + input_latent_list[::-1]

            video_num = len(whisper_chunks)
            gen = datagen(
                whisper_chunks=whisper_chunks,
                vae_encode_latents=input_latent_list_cycle,
                batch_size=batch_size,
                delay_frame=0,
                device=self._torch_device,
            )

            res_frame_list: list = []
            for whisper_batch, latent_batch in gen:
                audio_feature_batch = self.pe(whisper_batch)
                latent_batch = latent_batch.to(dtype=self._weight_dtype)
                logger.debug(
                    "UNet shapes: latent=%s, hidden=%s, timesteps=%s",
                    latent_batch.shape, audio_feature_batch.shape, self._timesteps.shape,
                )
                pred_latents = self.unet.model(
                    latent_batch,
                    self._timesteps,
                    encoder_hidden_states=audio_feature_batch,
                ).sample
                recon = self.vae.decode_latents(pred_latents)
                for res_frame in recon:
                    res_frame_list.append(res_frame)

            # Blend predicted face crops back into source frames (GPU-accelerated).
            cycle_len = len(coord_list_cycle)

            # Build per-frame input lists.  For v15 the y2 extra_margin is applied
            # here (same as the old loop) before passing to gpu_blend_batch so the
            # bbox semantics match what get_image always expected.
            ori_frames_batch: list = []
            bboxes_batch: list = []
            crops_batch: list = []

            for i, res_frame in enumerate(res_frame_list):
                bbox = coord_list_cycle[i % cycle_len]
                ori_frame = frame_list_cycle[i % cycle_len]
                x1, y1, x2, y2 = bbox
                if self.version == "v15":
                    y2 = min(y2 + extra_margin, ori_frame.shape[0])
                ori_frames_batch.append(ori_frame)
                bboxes_batch.append([x1, y1, x2, y2])
                crops_batch.append(res_frame)

            blended_frames = gpu_blend_batch(
                ori_frames_batch,
                crops_batch,
                bboxes_batch,
                face_parser=self.face_parser,
                parsing_mode=parsing_mode,
                version=self.version,
                device=self._torch_device,
            )

        # Encode to MP4 + mux audio via stdin pipe. Outside the GPU lock —
        # ffmpeg is CPU-bound, the GPU is free for the next job.
        out_name = result_name or "result.mp4"
        out_path = output_dir / out_name
        # Encode + audio mux in a single ffmpeg subprocess (no temp video file).
        # pipe_encoder defaults to libx264 -preset ultrafast: tutor sessions are
        # encode-time-sensitive, and the size penalty (~40% over -preset medium)
        # is acceptable on the dev backend. Task 4 may flip use_nvenc=True.
        encode_frames_to_mp4(
            frames=blended_frames,
            output_path=out_path,
            fps=fps,
            audio_path=audio_path,
            crf=18,
            use_nvenc=False,  # Task 4 may flip this
        )
        return out_path
