from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from detection import Detection


class DetectionWindow(QMainWindow):
    def __init__(self):
        super(DetectionWindow, self).__init__()
        loadUi('UI/detection_window.ui', self)
        self.stop_detection_button.clicked.connect(self.close)

    def create_detection_instance(self, token, location, receiver, camera_index_1, camera_index_2):
        self.detection = Detection(
            token, location, receiver, camera_index_1, camera_index_2
        )

    @pyqtSlot(QImage)
    def setImage1(self, image):
        self.label_detection_cam1.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot(QImage)
    def setImage2(self, image):
        self.label_detection_cam2.setPixmap(QPixmap.fromImage(image))

    def start_detection(self):
        self.detection.changePixmap1.connect(self.setImage1)
        self.detection.changePixmap2.connect(self.setImage2)
        self.detection.start()
        self.show()

    def closeEvent(self, event):
        self.detection.running = False
        event.accept()
