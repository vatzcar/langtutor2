"""Tests for trt_compile.py — torch.compile wrapper for MuseTalk UNet/VAE.

All GPU tests are skipped when CUDA is not available so the suite can run in
CI environments without a GPU. The warmup-failure test uses a CPU model.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
import torch
import torch.nn as nn

from trt_compile import try_compile, warmup_compiled_model


# ---------------------------------------------------------------------------
# Tiny model used across tests — fast to create, cheap to compile.
# ---------------------------------------------------------------------------

class _TinyLinear(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.fc = nn.Linear(16, 16)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(x)


class _RaisingModule(nn.Module):
    """Module whose forward always raises — used to test warmup fault tolerance."""

    def forward(self, *args, **kwargs):  # noqa: ANN001,ANN002,ANN003
        raise RuntimeError("intentional forward failure")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTryCompileInductorCuda:
    """On CUDA: compile a tiny nn.Linear, run a forward pass, verify shape."""

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_try_compile_inductor_cuda(self) -> None:
        model = _TinyLinear().cuda().half()
        compiled = try_compile(model, label="test_unet", backend="inductor", mode="default")
        # The compiled model is callable and produces correct output shapes.
        x = torch.randn(4, 16, device="cuda", dtype=torch.float16)
        with torch.no_grad():
            out = compiled(x)
        assert out.shape == (4, 16)


class TestTryCompileReturnsOriginalOnFailure:
    """Simulate compile failure; verify original model is returned and warning logged."""

    def test_try_compile_returns_original_on_unsupported(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        model = _TinyLinear()
        original_id = id(model)

        with patch("torch.compile", side_effect=RuntimeError("unsupported op")):
            with caplog.at_level(logging.WARNING, logger="avatar.trt_compile"):
                result = try_compile(model, label="unet_fail", backend="inductor")

        # Must return the *original* model unchanged.
        assert id(result) == original_id
        # Warning must have been emitted.
        assert any("torch.compile failed" in r.message for r in caplog.records)
        assert any("unet_fail" in r.message for r in caplog.records)


class TestTryCompileTensorrtFallback:
    """When torch_tensorrt import fails, fall back to inductor (or original on CPU)."""

    def test_try_compile_tensorrt_falls_back_when_missing(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        model = _TinyLinear()

        # Simulate torch_tensorrt not being installed.
        import builtins
        real_import = builtins.__import__

        def _fake_import(name: str, *args, **kwargs):  # noqa: ANN001,ANN002,ANN003
            if name == "torch_tensorrt":
                raise ImportError("No module named 'torch_tensorrt'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_fake_import):
            with caplog.at_level(logging.INFO, logger="avatar.trt_compile"):
                result = try_compile(model, label="vae_trt_test", backend="tensorrt")

        # Should log the fallback notice.
        assert any("torch_tensorrt not available" in r.message for r in caplog.records)
        # Result is either the compiled model (on CUDA) or the original (on CPU
        # where inductor may refuse to compile); either way it must be callable.
        x = torch.randn(2, 16)
        with torch.no_grad():
            out = result(x)
        assert out.shape == (2, 16)


class TestWarmupCompiledModel:
    """On CUDA: compile + warmup a tiny model without exceptions."""

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_warmup_compiled_model(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        model = _TinyLinear().cuda().half()
        compiled = try_compile(model, label="warmup_test", backend="inductor", mode="default")
        x = torch.randn(4, 16, device="cuda", dtype=torch.float16)

        with caplog.at_level(logging.INFO, logger="avatar.trt_compile"):
            warmup_compiled_model(compiled, (x,), label="warmup_test")

        assert any("warmup complete" in r.message for r in caplog.records)
        assert any("warmup_test" in r.message for r in caplog.records)


class TestWarmupSwallowsErrors:
    """warmup_compiled_model must NOT raise when the model's forward raises."""

    def test_warmup_swallows_errors(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        model = _RaisingModule()
        dummy = torch.zeros(1)

        # Must not raise.
        with caplog.at_level(logging.WARNING, logger="avatar.trt_compile"):
            warmup_compiled_model(model, (dummy,), label="raising_model")

        assert any("warmup failed" in r.message for r in caplog.records)
        assert any("raising_model" in r.message for r in caplog.records)
