"""MetaApi adapter. It stays disconnected until live mode and credentials both exist."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MetaApiStatus:
    state: str
    detail: str


def status(*, token: str, account_id: str, live_mode: str) -> MetaApiStatus:
    if live_mode != "live":
        return MetaApiStatus("SIMULATOR", "Paper mode is active. MetaApi is not connected.")
    if not token or not account_id:
        return MetaApiStatus("UNAVAILABLE", "MetaApi token or account id is missing.")
    try:
        import metaapi_cloud_sdk  # noqa: F401
    except ImportError:
        return MetaApiStatus("UNAVAILABLE", "metaapi-cloud-sdk is not installed. Use the live extra.")
    return MetaApiStatus("DEGRADED", "Credentials exist. Connect is explicit and is not opened during import.")
