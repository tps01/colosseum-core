from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from typing import Any


def normalize_iq_format(file_format: str, path: str) -> str:
    fmt = file_format.lower().lstrip(".")
    if fmt in {"bin", "mat", "iq.tar"}:
        return fmt
    suffix = Path(path).suffix.lower()
    if suffix == ".mat":
        return "mat"
    if suffix == ".bin":
        return "bin"
    if suffix == ".tar" or path.lower().endswith(".iq.tar"):
        return "iq.tar"
    return fmt


def write_iq_bin(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_iq_mat(path: Path, payload: bytes, *, metadata: dict[str, Any] | None = None) -> None:
    try:
        import numpy as np
        from scipy.io import savemat
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "file_format='mat' requires scipy and numpy; install scipy or use bin/iq.tar"
        ) from exc

    count = len(payload) // 8
    if count == 0:
        iq = np.array([], dtype=np.complex128)
    else:
        raw = np.frombuffer(payload[: count * 8], dtype="<f8")
        iq = raw[0::2] + 1j * raw[1::2]
    mat_data: dict[str, Any] = {"iq": iq}
    if metadata:
        mat_data["metadata"] = metadata
    path.parent.mkdir(parents=True, exist_ok=True)
    savemat(path, mat_data)


def write_iq_tar(path: Path, payload: bytes, *, metadata: dict[str, Any] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = metadata or {}
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        iq_info = tarfile.TarInfo(name="iq.bin")
        iq_info.size = len(payload)
        archive.addfile(iq_info, io.BytesIO(payload))
        meta_bytes = json.dumps(meta, indent=2).encode("utf-8")
        meta_info = tarfile.TarInfo(name="metadata.json")
        meta_info.size = len(meta_bytes)
        archive.addfile(meta_info, io.BytesIO(meta_bytes))
    path.write_bytes(buffer.getvalue())
