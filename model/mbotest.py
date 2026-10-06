from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "mbo_final.pt"
IMAGE_PATH = BASE_DIR / "seastar1.jpg"

model = YOLO(str(MODEL_PATH))

results = model.predict(
    source=str(IMAGE_PATH),
    conf=0.20,
    save=True
)

for result in results:
    print("\n[DETECTION RESULT]")

    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        class_name = model.names[class_id]

        print(
            f"class={class_name}, "
            f"confidence={confidence:.3f}"
        )