from pathlib import Path
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "yolo11n.pt"

DEFAULT_CONFIDENCE = 0.4


class MarineDetector:

    def __init__(
        self,
        model_path=MODEL_PATH,
        confidence=DEFAULT_CONFIDENCE
    ):
        self.confidence = confidence

        print("[VISION] Loading YOLO model...")
        print(f"[VISION] Model path: {model_path}")

        self.model = YOLO(str(model_path))

        print("[VISION] YOLO model loaded.")


    def _get_class_result(self, result, target_names):

        count = 0
        confidences = []

        if result.boxes is None:
            return 0, 0.0

        for box in result.boxes:

            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = self.model.names[class_id]

            if class_name.lower() in target_names:
                count += 1
                confidences.append(confidence)

        if count == 0:
            return 0, 0.0

        average_confidence = sum(confidences) / len(confidences)

        return count, average_confidence


    def detect(self, image):

        results = self.model.predict(
            source=image,
            conf=self.confidence,
            verbose=False
        )

        result = results[0]

        starfish_count, starfish_confidence = self._get_class_result(
            result,
            {
                "starfish",
                "sea star"
            }
        )

        shell_count, shell_confidence = self._get_class_result(
            result,
            {
                "shell",
                "seashell",
                "clam"
            }
        )

        observation = {
            "starfish_count": starfish_count,
            "starfish_confidence": round(
                starfish_confidence,
                3
            ),
            "shell_count": shell_count,
            "shell_confidence": round(
                shell_confidence,
                3
            )
        }

        return observation


    def annotate(self, image):

        results = self.model.predict(
            source=image,
            conf=self.confidence,
            verbose=False
        )

        result = results[0]

        return result.plot()