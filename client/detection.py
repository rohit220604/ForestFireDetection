from pathlib import Path

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QImage
import cv2
import time
import requests
from ultralytics import YOLO

MODEL_PATH = Path("model_files") / "yolo26n.pt"
OBJ_NAMES_PATH = Path("obj.names")
SAVED_FRAME_DIR = Path("saved_frame")
CONFIDENCE_THRESHOLD = 0.5
ALERT_COOLDOWN_SECONDS = 10


class Detection(QThread):
    changePixmap = pyqtSignal(QImage)

    def __init__(self, token, location, receiver):
        super(Detection, self).__init__()
        self.token = token
        self.location = location
        self.receiver = receiver
        self.running = False

    def _load_alert_classes(self):
        if not OBJ_NAMES_PATH.exists():
            return {"fire", "smoke", "flame", "forest fire"}
        with OBJ_NAMES_PATH.open("r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}

    def _is_fire_detection(self, class_name, alert_classes):
        name = class_name.lower()
        return name in alert_classes or any(token in name for token in ("fire", "smoke", "flame"))

    def run(self):
        self.running = True
        alert_classes = self._load_alert_classes()
        model = YOLO(str(MODEL_PATH))
        font = cv2.FONT_HERSHEY_PLAIN
        last_alert_time = 0.0

        cap = cv2.VideoCapture(0)

        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            height, width, channels = frame.shape
            fire_detected = False

            results = model(frame, verbose=False, conf=CONFIDENCE_THRESHOLD)
            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    label = result.names[class_id]
                    if not self._is_fire_detection(label, alert_classes):
                        continue

                    fire_detected = True
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    color = (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        frame,
                        f"{label} {confidence:.1%}",
                        (x1, y1 - 10),
                        font,
                        2,
                        color,
                        2,
                    )

            status = "FOREST FIRE DETECTED" if fire_detected else "No forest fire detected"
            status_color = (0, 0, 255) if fire_detected else (0, 200, 0)
            cv2.putText(frame, status, (10, 30), font, 2, status_color, 2)

            if fire_detected:
                now = time.time()
                if now - last_alert_time >= ALERT_COOLDOWN_SECONDS:
                    last_alert_time = now
                    self.save_detection(frame)

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            bytes_per_line = channels * width
            qt_image = QImage(
                rgb_image.data,
                width,
                height,
                bytes_per_line,
                QImage.Format_RGB888,
            )
            pixmap = qt_image.scaled(854, 540, Qt.KeepAspectRatio)
            self.changePixmap.emit(pixmap)

        cap.release()

    def save_detection(self, frame):
        SAVED_FRAME_DIR.mkdir(parents=True, exist_ok=True)
        frame_path = SAVED_FRAME_DIR / "frame.jpg"
        cv2.imwrite(str(frame_path), frame)
        print("Frame saved — forest fire alert")
        self.post_detection()

    def post_detection(self):
        frame_path = SAVED_FRAME_DIR / "frame.jpg"
        try:
            url = "https://forestfiredetection-y938.onrender.com/api/images/"
            headers = {"Authorization": "Token " + self.token}
            with frame_path.open("rb") as image_file:
                files = {"image": image_file}
                data = {
                    "user_ID": self.token,
                    "location": self.location,
                    "alert_receiver": self.receiver,
                }
                response = requests.post(url, files=files, headers=headers, data=data)

            if response.ok:
                print("Alert was sent to the server")
            else:
                print("Unable to send alert to the server")
        except OSError:
            print("Unable to save or read alert frame")
        except requests.RequestException:
            print("Unable to access server")
