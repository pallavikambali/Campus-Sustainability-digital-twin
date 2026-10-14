from pathlib import Path
from uuid import uuid4

from app.core.config import settings


class LocalImageStorage:
    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or settings.waste_image_storage_dir

    def save(self, image: bytes, extension: str) -> str:
        filename = f"{uuid4().hex}.{extension}"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        (self.storage_dir / filename).write_bytes(image)
        return f"local://waste-detections/{filename}"

    def delete(self, image_path: str) -> None:
        prefix = "local://waste-detections/"
        if not image_path.startswith(prefix):
            return
        filename = image_path.removeprefix(prefix)
        path = (self.storage_dir / filename).resolve()
        if path.parent == self.storage_dir.resolve() and path.is_file():
            path.unlink()