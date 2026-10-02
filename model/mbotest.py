from ultralytics import YOLO

MODEL_PATH = "models/mbo_yolo_best.pt"

model = YOLO(MODEL_PATH)

print("MBO-YOLO 로드 성공")
print(model.names)