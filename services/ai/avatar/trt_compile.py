"""torch.compile / torch_tensorrt wrapper for MuseTalk UNet and VAE decoder.

Public API:
  try_compile(model, label, backend="inductor", mode="max-autotune") -> nn.Module
  warmup_compiled_model(model, sample_input, label) -> None

Strategy:
  - Default backend "inductor": always available with PyTorch 2.x; JITs on
    first call (~30-60s) and gives 2-4x speedup on subsequent calls.
  - "tensorrt" backend: if torch_tensorrt is installed, prefer it. If import
    fails or compilation fails, fall back to inductor.
  - On any compilation failure, return the original model unchanged with a
    warning log. Compilation is purely opportunistic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import torch.nn as nn

logger = logging.getLogger("avatar.trt_compile")


def try_compile(
    model: "nn.Module",
    label: str,
    backend: str = "inductor",
    mode: str = "max-autotune",
) -> "nn.Module":
    """Wrap *model* with torch.compile (or torch_tensorrt) for faster inference.

    Falls back to the original model if compilation fails for any reason —
    compilation is purely opportunistic and must never crash the worker.

    Args:
        model: The nn.Module to compile (e.g. unet.model or vae.vae.decoder).
        label: Human-readable name used in log messages.
        backend: "inductor" (always available) or "tensorrt" (requires
            torch_tensorrt installed separately).
        mode: torch.compile mode passed through to the inductor backend.
            "max-autotune" tries all GEMM/conv kernels and picks the fastest.

    Returns:
        The compiled model (or the original on failure).
    """
    import torch

    effective_backend = backend

    if backend == "tensorrt":
        try:
            import torch_tensorrt  # noqa: F401
        except ImportError:
            logger.info(
                "torch_tensorrt not available, falling back to inductor for %s", label
            )
            effective_backend = "inductor"

    try:
        if effective_backend == "inductor":
            compiled = torch.compile(model, backend="inductor", mode=mode)
        else:
            # torch_tensorrt backend path — passes through torch.compile's
            # dispatcher which selects the TRT backend when available.
            compiled = torch.compile(model, backend="tensorrt")
        logger.info(
            "compiled %s with backend=%s mode=%s", label, effective_backend, mode
        )
        return compiled  # type: ignore[return-value]
    except Exception as exc:  # noqa: BLE001
        logger.warning("torch.compile failed for %s: %s", label, exc)
        return model


def warmup_compiled_model(
    model: "nn.Module",
    sample_input: tuple,
    label: str,
) -> None:
    """Run a dummy forward pass to trigger torch.compile JIT ahead of real use.

    The first call to a compiled model triggers trace + kernel compilation
    (~30-60 s for a UNet). Calling this at startup means the first real
    /render request is fast instead of paying the JIT cost in production.

    Args:
        model: A compiled (or plain) nn.Module.
        sample_input: Tuple of positional arguments to pass to model.forward().
            Shapes should exactly match real inference shapes (otherwise PyTorch
            will re-JIT on the first real call, paying ~30s) — any mismatch will
            cause torch.compile to re-JIT at inference time.
        label: Human-readable name for log messages.
    """
    import torch

    try:
        with torch.no_grad():
            model(*sample_input)
        logger.info("warmup complete for %s", label)
    except Exception as exc:  # noqa: BLE001
        logger.warning("warmup failed for %s: %s", label, exc)
