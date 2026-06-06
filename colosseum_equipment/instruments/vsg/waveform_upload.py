from __future__ import annotations

import ftplib  # nosec B402  # lab VSG waveform upload; bench config supplies FTP host
from pathlib import Path
from typing import Any

from colosseum_equipment.exceptions import EquipmentResponseError
from colosseum_equipment.protocols.scpi import SCPIHelper, wait_opc
from colosseum_equipment.transports.base import Transport

_FTP_WAVEFORM_DIR = "/USER/BBG1/WAVEFORM"


def _is_tcpip_resource(resource: str) -> bool:
    return resource.upper().startswith("TCPIP")


def _parse_visa_host(resource: str) -> str | None:
    if not _is_tcpip_resource(resource):
        return None
    parts = resource.split("::")
    if len(parts) >= 2 and parts[1]:
        return parts[1]
    return None


def _resolve_ftp_host(config: dict[str, Any]) -> str:
    if config.get("ftp_host"):
        return str(config["ftp_host"])
    host = _parse_visa_host(str(config.get("resource", "")))
    if host:
        return host
    raise EquipmentResponseError(
        "FTP waveform upload requires TCPIP resource or equipment.vsg ftp_host in bench config"
    )


def _iq_sample_count(payload: bytes) -> int:
    if len(payload) < 4 or len(payload) % 4 != 0:
        raise EquipmentResponseError(
            "IQ waveform .bin payload must contain whole 16-bit I/Q sample pairs"
        )
    return len(payload) // 4


def _supports_scpi_binary_upload(transport: Transport) -> bool:
    return callable(getattr(transport, "write_raw", None))


def _upload_via_scpi(scpi: SCPIHelper, remote_name: str, payload: bytes) -> None:
    scpi.write_binary_block(f'MMEM:DATA "{remote_name}"', payload)
    wait_opc(scpi)


def _remote_basename(remote_name: str, local_path: Path) -> str:
    if ":" in remote_name:
        return remote_name.rsplit(":", 1)[-1]
    return Path(remote_name).name or local_path.name


def _upload_via_ftp(
    config: dict[str, Any], local_path: Path, remote_name: str, payload: bytes
) -> None:
    host = _resolve_ftp_host(config)
    user = str(config.get("ftp_user", "anonymous"))
    password = str(config.get("ftp_password", ""))
    remote_basename = _remote_basename(remote_name, local_path)
    remote_path = f"{_FTP_WAVEFORM_DIR}/{remote_basename}"

    with ftplib.FTP(host, timeout=30) as ftp:  # nosec B321  # intentional instrument FTP fallback
        ftp.login(user=user, passwd=password)
        ftp.storbinary(f"STOR {remote_path}", _BytesIO(payload))


class _BytesIO:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            chunk = self._payload[self._offset :]
            self._offset = len(self._payload)
            return chunk
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def _apply_first_last_blanking(scpi: SCPIHelper, remote_name: str, sample_count: int) -> None:
    waveform_ref = remote_name if ":" in remote_name else f"WFM1:{remote_name}"
    scpi.write(f'RAD:ARB:MARK:CLEAR:ALL "{waveform_ref}",1')
    scpi.write(f'RAD:ARB:MARK:SET "{waveform_ref}",1,1,1,1,0')
    scpi.write(f'RAD:ARB:MARK:SET "{waveform_ref}",1,{sample_count},1,1,0')
    scpi.write("RAD:ARB:MDEStination:PULSe M1")


def upload_waveform_file(
    scpi: SCPIHelper,
    transport: Transport,
    config: dict[str, Any],
    local_path: str,
    remote_name: str,
    *,
    first_last_blanking: bool = False,
) -> None:
    path = Path(local_path)
    if path.suffix.lower() != ".bin":
        raise EquipmentResponseError(f"waveform upload expects a .bin file: {local_path}")
    payload = path.read_bytes()

    if _supports_scpi_binary_upload(transport):
        _upload_via_scpi(scpi, remote_name, payload)
    else:
        _upload_via_ftp(config, path, remote_name, payload)

    if first_last_blanking:
        _apply_first_last_blanking(scpi, remote_name, _iq_sample_count(payload))
