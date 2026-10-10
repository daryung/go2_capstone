from ultralytics import YOLOWorld

model = YOLOWorld("yolov8s-world.pt")

model.set_classes([
    "starfish",
    "sea star",
    "scallop",
    "seashell"
])

results = model.predict(
    source="../picture/seastar3.jpg",
    conf=0.1,
    imgsz=640,
    save=True
)

for box in results[0].boxes:
    cls = int(box.cls[0])
    print(model.names[cls], float(box.conf[0]))