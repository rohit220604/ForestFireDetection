from pathlib import Path

import cv2
import numpy as np
import requests
import time
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QImage
from ultralytics import YOLO

MODEL_PATH = Path("model_files") / "yolo26n.pt"
OBJ_NAMES_PATH = Path("obj.names")
SAVED_FRAME_DIR = Path("saved_frame")
CONFIDENCE_THRESHOLD = 0.5
ALERT_COOLDOWN_SECONDS = 10
DISPLAY_WIDTH = 420
DISPLAY_HEIGHT = 480
NO_CAMERA_WIDTH = 640
NO_CAMERA_HEIGHT = 480
API_BASE_URL = "https://forestfiredetection-y938.onrender.com/api"


class Detection(QThread):
    changePixmap1 = pyqtSignal(QImage)
    changePixmap2 = pyqtSignal(QImage)

    def __init__(self, token, location, receiver, camera_index_1=0, camera_index_2=0):
        super(Detection, self).__init__()
        self.token = token
        self.location = location
        self.receiver = receiver
        self.camera_index_1 = camera_index_1
        self.camera_index_2 = camera_index_2
        self.running = False

    def _load_alert_classes(self):
        if not OBJ_NAMES_PATH.exists():
            return {"fire", "smoke", "flame", "forest fire"}
        with OBJ_NAMES_PATH.open("r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}

    def _is_fire_detection(self, class_name, alert_classes):
        name = class_name.lower()
        return name in alert_classes or any(token in name for token in ("fire", "smoke", "flame"))

    def _create_no_camera_frame(self, camera_index):
        frame = np.full((NO_CAMERA_HEIGHT, NO_CAMERA_WIDTH, 3), 45, dtype=np.uint8)
        font = cv2.FONT_HERSHEY_SIMPLEX
        lines = [
            "No camera available",
            f"(index {camera_index})",
        ]
        y = NO_CAMERA_HEIGHT // 2 - 20
        for line in lines:
            (text_w, text_h), _ = cv2.getTextSize(line, font, 0.8, 2)
            x = (NO_CAMERA_WIDTH - text_w) // 2
            cv2.putText(frame, line, (x, y + text_h), font, 0.8, (200, 200, 200), 2)
            y += text_h + 16
        return frame

    def _annotate_frame(self, frame, model, alert_classes, font):
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
        return fire_detected, frame

    def _emit_frame(self, frame, signal):
        height, width, channels = frame.shape
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        bytes_per_line = channels * width
        qt_image = QImage(
            rgb_image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888,
        )
        pixmap = qt_image.scaled(DISPLAY_WIDTH, DISPLAY_HEIGHT, Qt.KeepAspectRatio)
        signal.emit(pixmap)

    def _try_open_camera(self, index):
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            cap.release()
            return None, False
        ret, _ = cap.read()
        if not ret:
            cap.release()
            return None, False
        return cap, True

    def notify_detection_started(self):
        try:
            url = f"{API_BASE_URL}/detection-started/"
            headers = {"Authorization": "Token " + self.token}
            data = {
                "location": self.location,
                "alert_receiver": self.receiver,
            }
            response = requests.post(url, headers=headers, data=data, timeout=45)
            try:
                body = response.json()
            except ValueError:
                body = {}

            recipient = body.get('recipient', self.receiver)
            if response.ok and body.get('email_queued'):
                print(
                    f"Email queued for {recipient} — check inbox/spam in 1–2 minutes."
                )
            elif response.ok and body.get('email_sent'):
                print(f"Email sent to {recipient}")
            elif response.status_code == 502:
                print(
                    "Server error (HTTP 502). Push latest server code and set "
                    "EMAIL_HOST_USER + EMAIL_HOST_PASSWORD on Render, then redeploy."
                )
            else:
                err = body.get('error', response.text[:300])
                print(f"Email NOT sent (HTTP {response.status_code}): {err}")
        except requests.RequestException as exc:
            print(f"Cannot reach server for email notification: {exc}")

    def run(self):
        self.running = True
        self.notify_detection_started()
        same_camera = self.camera_index_1 == self.camera_index_2
        placeholder1 = self._create_no_camera_frame(self.camera_index_1)
        placeholder2 = (
            placeholder1
            if same_camera
            else self._create_no_camera_frame(self.camera_index_2)
        )

        cap1, cam1_ok = self._try_open_camera(self.camera_index_1)
        if same_camera:
            cap2 = None
            cam2_ok = cam1_ok
        else:
            cap2, cam2_ok = self._try_open_camera(self.camera_index_2)

        model = None
        alert_classes = None
        font = cv2.FONT_HERSHEY_PLAIN
        if cam1_ok or cam2_ok:
            alert_classes = self._load_alert_classes()
            model = YOLO(str(MODEL_PATH))

        last_alert_time = 0.0

        while self.running:
            out1 = placeholder1
            out2 = placeholder2
            fire1 = False
            fire2 = False

            if cam1_ok and cap1 is not None:
                ret1, raw1 = cap1.read()
                if ret1:
                    fire1, out1 = self._annotate_frame(
                        raw1.copy(), model, alert_classes, font
                    )

            if same_camera:
                out2 = out1.copy()
                fire2 = fire1
            elif cam2_ok and cap2 is not None:
                ret2, raw2 = cap2.read()
                if ret2:
                    fire2, out2 = self._annotate_frame(
                        raw2.copy(), model, alert_classes, font
                    )

            if fire1 or fire2:
                now = time.time()
                if now - last_alert_time >= ALERT_COOLDOWN_SECONDS:
                    last_alert_time = now
                    if fire1:
                        alert_frame = out1
                    else:
                        alert_frame = out2
                    self.save_detection(alert_frame)

            self._emit_frame(out1, self.changePixmap1)
            self._emit_frame(out2, self.changePixmap2)

            if not cam1_ok and not cam2_ok:
                time.sleep(0.05)

        if cap1 is not None:
            cap1.release()
        if cap2 is not None:
            cap2.release()

    def save_detection(self, frame):
        SAVED_FRAME_DIR.mkdir(parents=True, exist_ok=True)
        frame_path = SAVED_FRAME_DIR / "frame.jpg"
        cv2.imwrite(str(frame_path), frame)
        print("Frame saved — forest fire alert")
        self.post_detection()

    def post_detection(self):
        frame_path = SAVED_FRAME_DIR / "frame.jpg"
        try:
            url = f"{API_BASE_URL}/images/"
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
