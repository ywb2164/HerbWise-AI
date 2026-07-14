from __future__ import annotations

import asyncio
import hashlib
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.integrations.contracts import (
    LocalVisionProvider,
    ModelCallContext,
    RecognitionCandidate,
    VisionRecognitionResult,
)
from app.integrations.openai_compatible import ProviderUnavailableError


class UltralyticsLocalVisionProvider(LocalVisionProvider):
    """Lazy, thread-safe local Ultralytics adapter. No model is imported at startup."""

    _lock = threading.Lock()
    _model: Any = None
    _model_path: str | None = None
    _load_ms: float | None = None

    def _load(self) -> Any:
        settings = get_settings()
        path = settings.resolved_local_model_path()
        if not settings.local_vision_enabled or not path.is_file():
            raise ProviderUnavailableError(
                "Local vision model is unavailable",
                error_code="local_model_unavailable",
            )
        with self._lock:
            if self._model is not None and self._model_path == str(path):
                return self._model
            started = time.perf_counter()
            try:
                from ultralytics import YOLO  # type: ignore[import-not-found]
            except ImportError as exc:
                raise ProviderUnavailableError(
                    "Ultralytics is not installed", error_code="local_model_unavailable"
                ) from exc
            self._model = YOLO(str(path))
            self._model_path = str(path)
            self._load_ms = round((time.perf_counter() - started) * 1000, 2)
            return self._model

    def _predict_sync(self, image_path: str) -> VisionRecognitionResult:
        settings = get_settings()
        model = self._load()
        started = time.perf_counter()
        try:
            results = model.predict(
                source=image_path,
                conf=settings.local_model_confidence_threshold,
                imgsz=settings.local_model_image_size,
                device=settings.local_model_device
                if settings.local_model_device != "auto"
                else None,
                verbose=False,
            )
            result = results[0]
            names = result.names
            candidates: list[RecognitionCandidate] = []
            for index, box in enumerate(result.boxes):
                if index >= settings.local_model_top_k:
                    break
                cls = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                xyxy = [float(value) for value in box.xyxy[0].tolist()]
                candidates.append(
                    RecognitionCandidate(
                        herb_name=str(names[cls]),
                        raw_name=str(names[cls]),
                        confidence=confidence,
                        rank=index + 1,
                        in_supported_catalog=False,
                        matched_by="training_class_name",
                        bbox=xyxy,
                    )
                )
        except Exception as exc:
            raise ProviderUnavailableError(
                "Local vision inference failed", error_code="local_model_unavailable"
            ) from exc
        return VisionRecognitionResult(
            provider="local",
            model_name=settings.resolved_local_model_path().name,
            candidate=candidates[0] if candidates else None,
            top_candidates=candidates,
            uncertainty="empty_detection" if not candidates else None,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            data_source="local",
        )

    async def predict_image(
        self, image_path: str | None, context: ModelCallContext
    ) -> VisionRecognitionResult:
        if image_path is None or not Path(image_path).is_file():
            raise ProviderUnavailableError(
                "Uploaded image is unavailable", error_code="unsupported_file"
            )
        result = await asyncio.to_thread(self._predict_sync, image_path)
        return result.model_copy(update={"file_id": context.file_id})

    @classmethod
    def status(cls) -> dict[str, object]:
        settings = get_settings()
        model_path = settings.resolved_local_model_path()
        return {
            "configured": settings.local_vision_enabled and model_path.is_file(),
            "loaded": cls._model is not None,
            "model_digest": hashlib.sha256(model_path.name.encode()).hexdigest()[:12]
            if model_path.is_file()
            else None,
            "load_ms": cls._load_ms,
        }
