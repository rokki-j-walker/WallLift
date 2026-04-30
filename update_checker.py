import json
import re
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from app_config import APP_VERSION, GITHUB_RELEASES_API_URL


INSTALLER_ASSET_SUFFIX = "setup-windows-x64.exe"


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    tag: str
    name: str
    download_url: str
    size: int


def normalize_version(version: str) -> str:
    return version.strip().lstrip("vV")


def version_tuple(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", normalize_version(version))
    return tuple(int(part) for part in parts) if parts else (0,)


def is_newer_version(candidate: str, current: str = APP_VERSION) -> bool:
    candidate_parts = version_tuple(candidate)
    current_parts = version_tuple(current)
    length = max(len(candidate_parts), len(current_parts))
    candidate_parts += (0,) * (length - len(candidate_parts))
    current_parts += (0,) * (length - len(current_parts))
    return candidate_parts > current_parts


def fetch_latest_update() -> UpdateInfo | None:
    request = urllib.request.Request(GITHUB_RELEASES_API_URL, headers={"User-Agent": "WallLift"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    tag = str(payload.get("tag_name") or "")
    if not tag or not is_newer_version(tag):
        return None

    for asset in payload.get("assets") or []:
        name = str(asset.get("name") or "")
        if name.endswith(INSTALLER_ASSET_SUFFIX):
            return UpdateInfo(
                version=normalize_version(tag),
                tag=tag,
                name=name,
                download_url=str(asset.get("browser_download_url") or ""),
                size=int(asset.get("size") or 0),
            )

    return None


def download_update_installer(update: UpdateInfo, progress_callback=None) -> Path:
    target_path = Path(tempfile.gettempdir()) / update.name
    part_path = target_path.with_suffix(target_path.suffix + ".part")

    request = urllib.request.Request(update.download_url, headers={"User-Agent": "WallLift"})
    with urllib.request.urlopen(request, timeout=30) as response:
        total = int(response.headers.get("Content-Length") or update.size or 0)
        done = 0

        with part_path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break

                output.write(chunk)
                done += len(chunk)

                if progress_callback:
                    progress_callback(done, total)

    if total > 0 and done != total:
        raise OSError(f"Incomplete download: expected {total} bytes, got {done} bytes")

    if done <= 0:
        raise OSError("Downloaded installer is empty")

    part_path.replace(target_path)
    return target_path
