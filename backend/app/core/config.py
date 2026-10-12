from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+pg8000://campus:local_dev_only@localhost:5432/campus_twin"
    cors_origins: str = "http://localhost:5173"
    waste_detector: str = "mock"
    waste_yolo_model_path: Path = PROJECT_ROOT / "backend" / "models" / "yolov8n.pt"
    waste_image_storage_dir: Path = (
        PROJECT_ROOT / "backend" / "storage" / "waste-detections"
    )
    waste_max_upload_bytes: int = Field(default=10_485_760, gt=0)
    waste_medium_object_threshold: int = Field(default=3, ge=1)
    waste_high_object_threshold: int = Field(default=5, ge=2)
    waste_candidate_classes: str = (
        "bottle,cup,can,plastic bag,paper,cardboard,carton,wrapper,food waste"
    )
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_timeout_seconds: float = Field(default=15.0, gt=0, le=120)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("waste_yolo_model_path", "waste_image_storage_dir", mode="before")
    @classmethod
    def resolve_project_path(cls, value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @model_validator(mode="after")
    def validate_waste_thresholds(self) -> "Settings":
        if self.waste_high_object_threshold <= self.waste_medium_object_threshold:
            raise ValueError("High waste threshold must exceed the medium threshold")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
