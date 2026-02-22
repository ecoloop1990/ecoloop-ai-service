"""
YOLOv8 model loader module.
Preloads the model at application startup to avoid reloading per request.
"""
import logging
from pathlib import Path
from typing import Optional

from ultralytics import YOLO

logger = logging.getLogger(__name__)


class ModelLoader:
    """Handles YOLOv8 model loading and inference."""

    def __init__(self, model_path: str = "best.pt"):
        """
        Initialize the model loader.

        Args:
            model_path: Path to the YOLOv8 model file (.pt)
        """
        self.model_path = model_path
        self.model: Optional[YOLO] = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the YOLOv8 model from disk."""
        try:
            model_file = Path(self.model_path)
            if not model_file.exists():
                logger.error(f"Model file not found at {self.model_path}")
                raise FileNotFoundError(f"Model file not found: {self.model_path}")

            logger.info(f"Loading YOLOv8 model from {self.model_path}")
            self.model = YOLO(self.model_path)
            logger.info("YOLOv8 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            raise

    def predict(self, image_path: str) -> list:
        """
        Run inference on an image.

        Args:
            image_path: Path to the image file

        Returns:
            List of detected objects with class names
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")

        try:
            logger.debug(f"Running inference on {image_path}")
            results = self.model(image_path, verbose=False)
            
            detected_items = []
            for result in results:
                # Extract class names from detections
                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        class_name = result.names[class_id]
                        detected_items.append(class_name)
            
            logger.info(f"Detected {len(detected_items)} objects: {detected_items}")
            return detected_items
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise

    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self.model is not None

