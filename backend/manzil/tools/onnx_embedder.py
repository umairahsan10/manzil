"""
Local ONNX embedder using Xenova/all-MiniLM-L6-v2.

No API calls, no PyTorch, no large dependencies.
Requires only: onnxruntime, tokenizers, numpy (all already installed).

Model files are downloaded once from HuggingFace and cached locally.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import List

import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_REPO_ID = "Xenova/all-MiniLM-L6-v2"
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache" / "manzil" / "embeddings"
_MODEL_PATH = _CACHE_DIR / "model.onnx"
_TOKENIZER_PATH = _CACHE_DIR / "tokenizer.json"
_CONFIG_PATH = _CACHE_DIR / "config.json"

_HF_URL = f"https://huggingface.co/{_REPO_ID}/resolve/main"

# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def _download_file(url: str, dest: Path) -> None:
    """Download a file if it doesn't exist."""
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("Downloading %s → %s", url, dest)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "manzil-onnx-embedder/1.0"},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        dest.write_bytes(response.read())


def _ensure_model_files() -> None:
    """Download ONNX model + tokenizer if missing."""
    _download_file(f"{_HF_URL}/onnx/model_quantized.onnx", _MODEL_PATH)
    _download_file(f"{_HF_URL}/tokenizer.json", _TOKENIZER_PATH)
    _download_file(f"{_HF_URL}/config.json", _CONFIG_PATH)


# ---------------------------------------------------------------------------
# ONNX embedder
# ---------------------------------------------------------------------------

class _OnnxEmbedder:
    """Lazy-loaded ONNX embedder."""

    def __init__(self) -> None:
        self._session = None
        self._tokenizer = None
        self._max_length = 256

    def _load(self) -> None:
        if self._session is not None:
            return

        _ensure_model_files()

        # Load tokenizer
        from tokenizers import Tokenizer  # type: ignore

        self._tokenizer = Tokenizer.from_file(str(_TOKENIZER_PATH))
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")

        # Read max length from config if available
        if _CONFIG_PATH.exists():
            cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            self._max_length = cfg.get("max_position_embeddings", 256)

        # Load ONNX model
        import onnxruntime as ort  # type: ignore

        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self._session = ort.InferenceSession(
            str(_MODEL_PATH),
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )

        log.info(
            "ONNX embedder loaded (%s, max_len=%d)",
            _MODEL_PATH.name,
            self._max_length,
        )

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Return L2-normalized embeddings for a list of texts."""
        self._load()
        assert self._tokenizer is not None and self._session is not None

        # Tokenize batch
        enc = self._tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in enc], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
        # BERT-style models expect token_type_ids (all zeros for single-sequence)
        token_type_ids = np.zeros_like(input_ids)

        # ONNX inference
        outputs = self._session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )
        # all-MiniLM-L6-v2 returns token embeddings [batch, seq_len, 384]
        token_embeddings = outputs[0]

        # Mean pooling with attention mask
        mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
        sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(mask_expanded, axis=1), a_min=1e-9, a_max=None)
        embeddings = sum_embeddings / sum_mask

        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.clip(norms, a_min=1e-12, a_max=None)

        return embeddings.tolist()


# Singleton
_EMBEDDER: _OnnxEmbedder | None = None


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed texts locally using ONNX all-MiniLM-L6-v2."""
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = _OnnxEmbedder()
    return _EMBEDDER.encode(texts)
