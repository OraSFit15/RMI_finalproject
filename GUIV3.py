import sys
import datetime

import PyQt5
import database
import pyaudio
import wave
import qt_material
import cv2
import pygame
import numpy as np
import bcrypt
import threading
from database import MovementData
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QToolTip, QMessageBox, QTableWidgetItem
from PyQt5.QtGui import QIcon, QFont, QImageReader
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtMultimedia import QSound, QMediaPlayer, QMediaContent, QAudioFormat, QAudioDeviceInfo, QAudioInput, \
    QAudioOutput
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtMultimedia import QCamera, QCameraImageCapture, QCameraInfo, QAbstractVideoSurface, QVideoFrame
from PyQt5.QtMultimediaWidgets import QCameraViewfinder
from pymongo.errors import PyMongoError


class CaptureThread(QThread):
    """A thread to capture frames from the default camera at 60 fps."""

    capture_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        """Initializes the CaptureThread class."""
        super().__init__()
        self.cap = None
        self.running = False

    def run(self):
        """Starts the thread to capture frames from the camera."""
        self.running = True
        self.cap = cv2.VideoCapture(0)
        # Set capture rate to 60 fps
        self.cap.set(cv2.CAP_PROP_FPS, 60)

        while self.running:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (704, 576))
                self.capture_signal.emit(frame)

    def stop(self):
        """Stops the capture thread and releases the camera."""
        self.running = False
        if self.cap is not None:
            self.cap.release()


class ProcessThread(QThread):
    """A thread to process captured frames."""

    processed_frame_signal = pyqtSignal(np.ndarray, bool, float)

    def __init__(self, optical_flow_app):
        """Initializes the ProcessThread class.

        Args:
            optical_flow_app (OpticalFlowApplication): An instance of the OpticalFlowApplication class
                for processing the captured frames.
        """
        super().__init__()
        self.optical_flow_app = optical_flow_app
        self.input_frame = None

    def input_frame_slot(self, frame):
        """Receives input frames from the capture thread.

        Args:
            frame (np.ndarray): The input frame captured by the camera.
        """
        self.input_frame = frame

    def run(self):
        """Starts the thread to process captured frames."""
        while True:
            if self.input_frame is not None:
                self.process_frame(self.input_frame)
                self.input_frame = None

    def process_frame(self, frame):
        """Processes the frame using the provided optical flow application.

        Args:
            frame (np.ndarray): The frame to be processed using optical flow.
        """
        prev_gray, movement_detected, movement_value = self.optical_flow_app.process_optical_flow(
            frame, self.optical_flow_app.prev_gray
        )

        self.processed_frame_signal.emit(frame, movement_detected, movement_value)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.optical_flow_app.prev_gray = gray


class OpticalFlowApp(QWidget):
    """A widget for an application to process optical flow in real-time."""

    def __init__(self, parent, parent_widget):
        """Initializes the OpticalFlowApp class.

        Args:
            parent (QWidget): The parent widget.
            parent_widget (QWidget): The parent widget where this OpticalFlowApp is used.
        """
        super().__init__(parent)
        self.parent_widget = parent_widget
        self.prev_gray = None
        self.viewfinder = QLabel(self)
        self.viewfinder.setGeometry(20, 50, 640, 480)
        self.threshold = None

        self.capture_thread = CaptureThread()
        self.process_thread = ProcessThread(self)

        self.capture_thread.capture_signal.connect(self.process_thread.input_frame_slot)
        self.process_thread.processed_frame_signal.connect(self.display_frame)

        self.capture_thread.start()
        self.process_thread.start()

    def display_frame(self, frame, movement_detected, movement_value):
        """Displays the processed frame in the widget and updates labels based on movement detection.

        Args:
            frame (np.ndarray): The processed frame to display.
            movement_detected (bool): Indicates whether movement is detected in the frame.
            movement_value (float): The calculated movement value.
        """
        if movement_detected:
            self.parent_widget.movement_detected_result_label.setText("Yes")
            self.parent_widget.movement_detected_result_label.setStyleSheet("font-size: 12px; color: green;")

            if self.parent_widget.collect_movement_data:
                movement_data = {
                    "movement_detected": movement_detected,
                    "movement_value": movement_value,
                    "timestamp": datetime.utcnow(),
                }
                self.parent_widget.movement_count += 1
                self.parent_widget.current_test_data.append(movement_data)
        else:
            self.parent_widget.movement_detected_result_label.setText("No")
            self.parent_widget.movement_detected_result_label.setStyleSheet("font-size: 12px; color: red;")

        self.parent_widget.movement_value_label.setText(f"Movement Value: {movement_value:.2f}")

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        # Calculate the appropriate QLabel size based on the video feed's aspect ratio
        viewfinder_width = 600
        viewfinder_height = 450
        self.parent_widget.viewfinder.setFixedSize(viewfinder_width, viewfinder_height)
        qimage = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        self.parent_widget.viewfinder.setPixmap(pixmap)

    def process_optical_flow(self, frame, prev_gray):
        """Processes the frame to detect optical flow and movements.

        Args:
            frame (np.ndarray): The frame to process.
            prev_gray (np.ndarray): The previous grayscale frame.

        Returns:
            Tuple[np.ndarray, bool, float]: A tuple containing the updated previous grayscale frame,
                a boolean indicating whether movement is detected, and the calculated movement value.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        gray = cv2.convertScaleAbs(gray, alpha=1, beta=-50)
        movement_detected = False
        movement_value = 0

        if prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 6, 5, 1.2, 0)
            magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

            if self.parent_widget.threshold is None:
                self.threshold = np.max(np.mean(magnitude[:500])) + 0.05  # Calculate threshold once
                self.parent_widget.threshold = self.threshold
                print(f"Threshold: {self.threshold}")

            movement_detected = np.mean(magnitude) > self.threshold
            movement_value = np.mean(magnitude)

            # Visualization
            hsv = np.zeros((frame.shape[0], frame.shape[1], 3), dtype=np.float32)
            hsv[..., 1] = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[..., 1]
            hsv[..., 0] = 0.5 * 180
            hsv[..., 2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
            color = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        prev_gray = gray
        return prev_gray, movement_detected, movement_value



class FramelessWindow(QMainWindow):
    """A frameless window with a title bar."""

    def __init__(self, title=""):
        """Initializes the FramelessWindow class.

        Args:
            title (str): The title of the window (default: "").
        """
        super().__init__()
        self.mousePress = None
        self.moveWindow = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.title_bar = TitleBar(self, title)
        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.addWidget(self.title_bar)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)
        self.title_separator = QFrame(self.central_widget)
        self.title_separator.setGeometry(0, 30, self.width(), 2)
        self.title_separator.setStyleSheet("background-color: orange;")

        self.setFixedSize(500, 300)
    """def paintEvent(self, event):
        
        painter = QPainter(self)
        pen = QPen(QColor("#cc692f"), 30, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawRect(self.rect())"""
    def mousePressEvent(self, event):
        """Event handler for mouse press events."""
        self.mousePress = event.pos()

    def mouseMoveEvent(self, event):
        """Event handler for mouse move events."""
        if self.mousePress is None:
            return
        self.moveWindow = event.globalPos() - self.mousePress
        self.move(self.moveWindow)

    def mouseReleaseEvent(self, event):
        """Event handler for mouse release events."""
        self.mousePress = None
        self.moveWindow = None


class CustomDialog(QDialog):
    """A custom dialog window with a title bar."""

    def __init__(self, parent=None, title="My Dialog Title"):
        """Initializes the CustomDialog class.

        Args:
            parent (QWidget): The parent widget (default: None).
            title (str): The title of the dialog (default: "My Dialog Title").
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.title_bar = TitleBar(self, title)
        self.setGeometry(300, 300, 300, 300)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.title_bar)
        self.setLayout(self.main_layout)
        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)

    def mousePressEvent(self, event):
        """Event handler for mouse press events."""
        self.mousePress = event.pos()

    def mouseMoveEvent(self, event):
        """Event handler for mouse move events."""
        if self.mousePress is None:
            return
        self.moveWindow = event.globalPos() - self.mousePress
        self.move(self.moveWindow)

    def mouseReleaseEvent(self, event):
        """Event handler for mouse release events."""
        self.mousePress = None
        self.moveWindow = None



class TitleBar(QWidget):
    """A custom title bar for the window."""

    def __init__(self, parent, title="Mock MRI"):
        """Initializes the TitleBar class.

        Args:
            parent (QWidget): The parent widget.
            title (str): The title to display on the title bar (default: "Mock MRI").
        """
        super().__init__()
        self.parent = parent
        self.setFixedHeight(30)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.layout.addSpacing(5)
        self.layout.addWidget(QLabel(title, self))
        self.layout.addStretch()
        minimize = self.layout.addWidget(TitleButton("-", self))
        exit = self.layout.addWidget(TitleButton("X", self))
        self.layout.addSpacing(5)


class TitleButton(QPushButton):
    """A custom button for the title bar."""

    def __init__(self, title, parent):
        """Initializes the TitleButton class.

        Args:
            title (str): The title of the button.
            parent (QWidget): The parent widget.
        """
        super().__init__(title, parent)
        self.parent = parent
        self.setFixedWidth(20)
        self.setFixedHeight(20)
        self.clicked.connect(self.clickedEvent)

    def clickedEvent(self):
        """Handles the button's click event."""
        if self.text() == "X":
            self.parent.parent.close()
        elif self.text() == "-":
            self.parent.parent.showMinimized()


class Login(FramelessWindow):
    """The login window for the Mock MRI Scanner application."""

    def __init__(self):
        """Initializes the Login class."""
        super().__init__(title="MOCK MRI SCANNER")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.init_ui()
        self.init_geometry()
        self.client = database.get_client()
        self.db = self.client["MRI_PROJECT"]
        self.user_collection = self.db["USERS"]
        self.users = database.Users(self.user_collection)
        # print(f"user_collection: {self.user_collection}, users: {self.users}")
        # print(self.user_collection.find_one({"username": "admin"}))

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)
        self.layout.addWidget(self.container)

        self.init_login_button()
        self.init_username()
        self.init_password()
        self.init_appname()
        self.init_appline()
        self.show()

    def init_ui(self):
        """Initializes the user interface of the Login window."""
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("Login")



    def init_geometry(self):
        """Sets up the initial geometry of the Login window."""
        self.top = 100
        self.left = 100
        self.width = 500
        self.height = 220
        self.setGeometry(self.top, self.left, self.width, self.height)
        self.setStyleSheet("QWidget { border-radius: 20px;background-color: #fbe5d6;  }")


    def init_login_button(self):
        """Initializes the Login button."""
        self.login = QPushButton(self.central_widget)
        self.login.setText("LOGIN")
        self.login.setGeometry(215, 150, 80, 20)
        self.login.setFont(QFont('Roboto', 12))
        self.login.setStyleSheet(
            " border-radius : 5px; font-size: 10px; background-color:  #f8cba8; color: black;"
            "QPushButton { border-radius: 30px; }")
        self.login.setCursor(Qt.PointingHandCursor)

        self.login.clicked.connect(self.login_clicked)

    def init_username(self):
        """Initializes the Username label and input field."""
        self.username = QLabel(self.central_widget)
        self.username.setText("USERNAME:")
        self.username.move(95, 95)
        self.username.setFont(QFont('Roboto', 12))
        self.username.setStyleSheet("font-size: 15px;")
        self.username_input = QLineEdit(self.central_widget)
        self.username_input.setGeometry(180, 100, 200, 20)
        self.username_input.setFont(QFont('Roboto', 15))
        self.username_input.setStyleSheet("font-size: 15px;background-color:white;")

    def init_password(self):
        """Initializes the Password label and input field."""
        self.password = QLabel(self.central_widget)
        self.password.setText("PASSWORD:")
        self.password.move(95, 120)
        self.password.setFont(QFont('Roboto', 12))
        self.password.setStyleSheet("font-size: 15px;")

        self.password_input = QLineEdit(self.central_widget)
        self.password_input.setGeometry(180, 125, 200, 20)
        self.password_input.setFont(QFont('Roboto', 15))
        self.password_input.setStyleSheet("font-size: 15px;background-color:white;")
        self.password_input.setEchoMode(QLineEdit.Password)

    def init_appname(self):
        """Initializes the application name label."""
        self.appname = QLabel(self.central_widget)
        self.appname.setText("Welcome, insert your credentials to continue")
        self.appname.move(60, 50)
        self.appname.setFont(QFont('Roboto', 12))
        self.appname.setStyleSheet("font-size: 20px;")
        self.appname.adjustSize()

    def init_appline(self):
        """Initializes the horizontal lines below the labels and input fields."""
        self.appline = QFrame(self.central_widget)
        self.appline.setGeometry(100, 80, 300, 2)
        self.appline.setStyleSheet("background-color: #f8cbad;")

        self.appline2 = QFrame(self.central_widget)
        self.appline2.setGeometry(100, 180, 300, 2)
        self.appline2.setStyleSheet("background-color: #f8cbad;")

    def login_clicked(self):
        """Handles the click event of the Login button."""
        username = self.username_input.text()
        password = self.password_input.text()

        if self.users.check_user(username, password):
            self.main = MenuWindow()
            self.main.show()
            self.close()
        else:
            QMessageBox.about(self, "Error", "Wrong username or password")


class MenuWindow(FramelessWindow):
    def __init__(self):
        """Initializes the Login class."""
        super().__init__(title="Mock MRI Scanner")
        self.stat = None
        self.set = None
        self.exs = None
        self.new = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.label = QLabel("Movement Monitor MRI",self)
        self.label.setGeometry(135,50,100,50)
        self.label.setFixedSize(500, 65)
        self.label.setStyleSheet(
            " font-size: 20px;  color: black;font-weight: bold;"
            )
        self.init_ui()
        self.init_geometry()
        self.client = database.get_client()
        self.db = self.client["MRI_PROJECT"]
        self.user_collection = self.db["USERS"]
        self.users = database.Users(self.user_collection)
        # print(f"user_collection: {self.user_collection}, users: {self.users}")
        # print(self.user_collection.find_one({"username": "admin"}))

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)
        self.layout.addWidget(self.container)

        self.init_new_button()
        self.init_exs_button()
        self.init_stat_button()
        self.init_set_button()
        self.new_participant_dialog = NewParticipantDialog()
        self.existing_participant_dialog = ExistingParticipantDialog()


        self.show()

    def init_ui(self):
        """Initializes the user interface of the Login window."""
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("Login")

    def close_window(self):
        self.close()
    def init_geometry(self):
        """Sets up the initial geometry of the Login window."""
        self.top = 450
        self.left = 100
        self.width = 550
        self.height = 200
        self.setGeometry(self.top, self.left, self.width, self.height)
        self.setStyleSheet("QWidget { border-radius: 20px;background-color: #f8cba8; }")

    def show_new_participant_dialog(self):
        self.new_participant_dialog.show()
    def show_exs_participant_dialog(self):
        self.existing_participant_dialog.show()

    def init_new_button(self):
        """Initializes the Login button."""
        self.new = QPushButton(self.central_widget)
        self.new.setFixedSize(150, 65)
        self.new.setText("NEW PARTICIPANT")
        self.new.setGeometry(50, 120, 80, 20)
        self.new.setFont(QFont('Roboto', 12))
        self.new.setStyleSheet(
            " border: 1px solid #c55b26; font-size: 12px;"
            " background-color:  #fbe5d6; color: black;font-weight: bold;"
        )
        self.new.setCursor(Qt.PointingHandCursor)

        self.new.clicked.connect(self.show_new_participant_dialog)
        self.new.clicked.connect(self.close_window)

    def init_exs_button(self):
        """Initializes the Login button."""
        self.exs = QPushButton(self.central_widget)
        self.exs.setFixedSize(150, 65)
        self.exs.setText("EXISTING PARTICIPANT")
        self.exs.setGeometry(300, 120, 100, 20)
        self.exs.setFont(QFont('Roboto', 12))
        self.exs.setStyleSheet(
            "  border: 1px solid #c55b26; font-size: 12px;"
            " background-color:  #fbe5d6; color: black;font-weight: bold;"
        )
        self.exs.setCursor(Qt.PointingHandCursor)
        self.exs.clicked.connect(self.show_exs_participant_dialog)
        self.exs.clicked.connect(self.close_window)

    def init_stat_button(self):
        """Initializes the Login button."""
        self.stat = QPushButton(self.central_widget)
        self.stat.setFixedSize(150, 65)
        self.stat.setText("STATISTICS")
        self.stat.setGeometry(50, 200, 80, 20)
        self.stat.setFont(QFont('Roboto', 12))
        self.stat.setStyleSheet(
            "  border: 1px solid #c55b26 ; font-size: 12px;"
            " background-color:  #fbe5d6; color: black;font-weight: bold;"
        )
        self.stat.setCursor(Qt.PointingHandCursor)
        self.stat.clicked.connect(self.close_window)
        #self.stat.clicked.connect(self.login_clicked)

    def init_set_button(self):
        """Initializes the Login button."""
        self.set = QPushButton(self.central_widget)
        self.set.setFixedSize(150, 65)
        self.set.setText("SETTINGS")
        self.set.setGeometry(300, 200, 80, 20)
        self.set.setFont(QFont('Roboto', 12))
        self.set.setStyleSheet(
            "  border: 1px solid #c55b26 ; font-size: 12px;"
            " background-color:  #fbe5d6; color: black;font-weight: bold;"
        )
        self.set.setCursor(Qt.PointingHandCursor)
        self.set.clicked.connect(self.close_window)
        #self.login.clicked.connect(self.login_clicked)


class SoundLoader(QThread):
    """A thread to load sound files in the background."""

    sound_loaded = pyqtSignal()

    def __init__(self, sound_file):
        """Initializes the SoundLoader class.

        Args:
            sound_file (str): The path to the sound file to be loaded.
        """
        super().__init__()
        self.sound_file = sound_file
        self.sound = None

    def run(self):
        """Runs the thread to load the sound file."""
        self.sound = pygame.mixer.Sound(self.sound_file)
        self.sound_loaded.emit()


class MicrophoneRecorder:
    """A class to record audio from the microphone."""

    def __init__(self):
        """Initializes the MicrophoneRecorder class."""
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.outstream = None
        self._setup_microphone()
        self.recording = False

    def _setup_microphone(self):
        """Sets up the microphone for recording."""
        try:
            self.stream = self.p.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      frames_per_buffer=1024)
            self.outstream = self.p.open(format=pyaudio.paInt16,
                                         channels=1,
                                         rate=44100,
                                         output=True,
                                         frames_per_buffer=1024)
        except IOError:
            self.stream = None
            self.outstream = None

    def is_microphone_ready(self):
        """Checks if the microphone is ready for recording.

        Returns:
            bool: True if the microphone is ready, False otherwise.
        """
        return self.stream is not None and self.outstream is not None

    def start(self):
        """Starts the microphone recording."""
        if self.is_microphone_ready():
            self.recording = True
            self.thread = threading.Thread(target=self._record)
            self.thread.start()

    def stop(self):
        """Stops the microphone recording."""
        self.recording = False
        self.thread.join()

    def _record(self):
        """Records audio from the microphone."""
        while self.recording:
            data = self.stream.read(1024)
            self.outstream.write(data)

    def close(self):
        """Closes the microphone stream and terminates the PyAudio instance."""
        if self.is_microphone_ready():
            self.stream.stop_stream()
            self.stream.close()
            self.outstream.stop_stream()
            self.outstream.close()
        self.p.terminate()


class ParticipantDetailsWindow(QDialog):
    """A window for handling participant details."""

    participant_id_received = pyqtSignal(str)

    def __init__(self, parent=None, title="PARTICIPANT PROFILE"):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(450, 100, 550, 200)

        # Initialize the main layout
        self.main_layout = QVBoxLayout()
        self.left_group_box = QGroupBox()
        self.left_group_box.setFixedSize(400, 500)

        self.right_group_box = QGroupBox()
        self.right_group_box.setFixedSize(400, 500)


        # Create a title bar
        self.title_bar = TitleBar(self, title)
        self.main_layout.addWidget(self.title_bar)

        # Add a separator
        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)
        label_styles_1 = """
            QLabel {
                background-color: #fbe5d6;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 3px;
            }
        """

        # Create layouts for left and right columns
        self.columns_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()

        # Widgets for the left column
        self.left_layout.addWidget(QLabel("ID NUMBER :"))
        self.id_field = QLabel()
        self.id_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.id_field)

        self.left_layout.addWidget(QLabel("First Name:"))
        self.first_name_field = QLabel()
        self.first_name_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.first_name_field)

        self.left_layout.addWidget(QLabel("Last Name:"))
        self.last_name_field = QLabel()
        self.last_name_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.last_name_field)

        self.left_layout.addWidget(QLabel("Birthdate:"))
        self.birthdate_field = QLabel()
        self.birthdate_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.birthdate_field)

        self.left_layout.addWidget(QLabel("Age:"))
        self.age_field = QLabel()
        self.age_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.age_field)

        self.left_layout.addWidget(QLabel("Gender:"))
        self.gender_field = QLabel()
        self.gender_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.gender_field)

        self.left_layout.addWidget(QLabel("Email:"))
        self.email_field = QLabel()
        self.email_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.email_field)

        # Widgets for the right column
        self.right_layout.addWidget(QLabel("Level of Anxiety:"))
        self.level_anxiety_field = QLabel()
        self.level_anxiety_field.setStyleSheet(label_styles_1)
        self.right_layout.addWidget(self.level_anxiety_field)

        self.submit_button_side = QPushButton("ADDITIONAL INFORMATION")
        self.submit_button_side.setCursor(Qt.PointingHandCursor)
        self.right_layout.addWidget(self.submit_button_side)

        # Créer un layout horizontal pour la ligne des boutons
        self.button_layout_1 = QHBoxLayout()
        self.button_layout_2 = QHBoxLayout()

        self.hist_anx = QPushButton("HISTORY\nOF ANXIETY LEVEL\nCHANGES")
        self.hist_anx.setCursor(Qt.PointingHandCursor)
        self.button_layout_1.addWidget(self.hist_anx)
        self.hist_anx.setFixedSize(150, 65)

        self.hist_mri = QPushButton("HISTORY\nOF\nMRI TEST")
        self.hist_mri.setCursor(Qt.PointingHandCursor)
        self.button_layout_1.addWidget(self.hist_mri)
        self.hist_mri.setFixedSize(150, 65)

        self.right_layout.addLayout(self.button_layout_1)

        self.changes = QPushButton("MAKE CHANGES")
        self.changes.setCursor(Qt.PointingHandCursor)
        self.button_layout_2.addWidget(self.changes)
        self.changes.setFixedSize(150, 65)

        self.test = QPushButton("BEGIN TEST")
        self.test.setCursor(Qt.PointingHandCursor)
        self.button_layout_2.addWidget(self.test)
        self.test.setFixedSize(150, 65)

        self.right_layout.addLayout(self.button_layout_2)
        self.right_layout.addStretch()

        self.left_group_box.setLayout(self.left_layout)
        self.right_group_box.setLayout(self.right_layout)

        columns_layout = QHBoxLayout()
        columns_layout.addWidget(self.left_group_box)
        columns_layout.addWidget(self.right_group_box)

        # Add left and right layouts to the columns layout
        self.columns_layout.addWidget(self.left_group_box)
        self.columns_layout.addWidget(self.right_group_box)
        # Add the columns layout to the main layout
        self.main_layout.addLayout(self.columns_layout)

        # Set the main layout for the dialog
        self.setLayout(self.main_layout)


        self.setStyleSheet("""
                QDialog {
                    background-color: #f8cba8;
                }
                QLabel {
                color: black;
                font-weight: bold;
                background-color: #f8cba8;
            }
                QLineEdit, QComboBox, QDateEdit {
                    background-color: #fbe5d6;
                    border: 1px solid #c55b26;
                    border-radius: 5px;
                    padding: 3px;
                }
                QPushButton {
                    background-color: #f4b283;
                    color: black;
                    font-weight: bold;
                    border: 1px solid #c55b26;
                    border-radius: 5px;
                    padding: 6px;
                }
                QPushButton:pressed {
                    background-color: #8c3e13;
                }
            """)

    def show_details(self, participant_details):
        """Affiche les détails du participant dans la fenêtre."""
        self.first_name_field.setText(f" {participant_details['first_name']}")
        self.last_name_field.setText(f" {participant_details['last_name']}")
        self.age_field.setText(f" {participant_details['age']}")
        self.id_field.setText(f" {participant_details['id']}")

    def handle_participant_id(self, participant_id):
        """Handles the participant ID received from the caller.

        Args:
            participant_id (str): The ID of the selected participant.
        """
        participant = database.find_participant(participant_id)
        if participant:
            participant_details_window = ParticipantDetailsWindow()
            participant_details_window.show_details(participant)
            participant_details_window.show()
        else:
            # Handle the case when the participant is not found
            print(f"Participant with ID {participant_id} not found.")

    def mousePressEvent(self, event):
        """Event handler for mouse press events."""
        self.mousePress = event.pos()

    def mouseMoveEvent(self, event):
        """Event handler for mouse move events."""
        if self.mousePress is None:
            return
        self.moveWindow = event.globalPos() - self.mousePress
        self.move(self.moveWindow)

    def mouseReleaseEvent(self, event):
        """Event handler for mouse release events."""
        self.mousePress = None
        self.moveWindow = None

class NewParticipantDialog(QDialog):
    """A dialog for entering information about a new participant."""
    participant_id_generated = pyqtSignal(str)

    def __init__(self, parent=None, title="NEW PARTICIPANT FORM"):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(450, 100, 550, 200)

        # Initialize main layout
        self.main_layout = QVBoxLayout()

        # Add title bar to main layout
        self.title_bar = TitleBar(self, title)
        self.main_layout.addWidget(self.title_bar)

        self.label_email = QLabel("Email:")
        self.email_field = QLineEdit()
        self.label_level_anxiety = QLabel("Level of Anxiety:")
        self.level_anxiety_field = QLineEdit()
        self.contact_number_label = QLabel("Contact Number")
        self.contact_number_field = QLineEdit()
        self.submit_button_side = QPushButton("ADDITIONAL INFORMATION")
        self.submit_button_side.setCursor(Qt.PointingHandCursor)

        self.first_name_field = QLineEdit()
        self.last_name_field = QLineEdit()
        self.id_number_label = QLabel("Id Number:")
        self.id_number_field = QLineEdit()
        self.sex_field = QComboBox()
        self.sex_field.addItems(['Male', 'Female', 'Other'])
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.age_label = QLabel()
        self.selected_date_label = QLabel()
        self.submit_button = QPushButton("SAVE")
        self.submit_button.clicked.connect(self.submit)
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.title_bar)

        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)

        self.columns_layout = QHBoxLayout()

        self.right_layout = QVBoxLayout()
        self.right_layout.addWidget(self.label_email)
        self.right_layout.addWidget(self.email_field)
        self.right_layout.addWidget(self.label_level_anxiety)
        self.right_layout.addWidget(self.level_anxiety_field)
        self.right_layout.addWidget(self.contact_number_label)
        self.right_layout.addWidget(self.contact_number_field)
        self.right_layout.addWidget(self.submit_button_side)
        self.right_layout.addWidget(self.submit_button)
        self.right_layout.addStretch()

        self.left_layout = QVBoxLayout()
        self.left_layout.addWidget(QLabel("First Name:"))
        self.left_layout.addWidget(self.first_name_field)
        self.left_layout.addWidget(QLabel("Last Name:"))
        self.left_layout.addWidget(self.last_name_field)
        self.left_layout.addWidget(QLabel("Gender:"))
        self.left_layout.addWidget(self.sex_field)
        self.left_layout.addWidget(self.id_number_label)
        self.left_layout.addWidget(self.id_number_field)
        self.left_layout.addWidget(QLabel("Date of Birth:"))
        self.left_layout.addWidget(self.date_edit)
        self.left_layout.addWidget(self.selected_date_label)

        # Add columns to main layout
        self.columns_layout.addLayout(self.left_layout)
        self.columns_layout.addLayout(self.right_layout)

        # Add columns layout to main layout
        self.main_layout.addLayout(self.columns_layout)

        # Connect dateChanged signal
        # Apply styles
        self.setStyleSheet("""
            QDialog {
                background-color: #f8cba8;
            }
            QLabel {
                color: black;
                font-weight: bold;
                background-color: #f8cba8;
            }
            QLineEdit, QComboBox, QDateEdit {
                background-color: #fbe5d6;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 3px;
            }
            QPushButton {
                background-color: #f4b283;
                color: black;
                font-weight: bold;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:pressed {
                background-color: #8c3e13;
            }
        """)

    def show_participantdetails(self):
        self.details_window.show()

    def submit(self):
        # Vérifier si les champs requis sont vides
        if self.first_name_field.text() == '' or self.last_name_field.text() == '':
            QMessageBox.warning(self, "Warning", "Please fill in all required fields.")
            return

        selected_date = self.date_edit.date().toPyDate()
        selected_date_str = selected_date.strftime("%Y-%m-%d")
        self.selected_date_label.setText(selected_date_str)
        print(selected_date_str)

        selected_date = datetime.datetime(selected_date.year, selected_date.month, selected_date.day)
        current_date = datetime.datetime.now()
        age = current_date.year - selected_date.year - (
                (current_date.month, current_date.day) < (selected_date.month, selected_date.day))

        if age < 0:
            QMessageBox.warning(self, "Warning", "Invalid date of birth.")
            return

        success = database.insert_participant(
            self.first_name_field.text(),
            self.last_name_field.text(),
            age,
            self.sex_field.currentText()
        )

        if success:
            self.participant_id_generated.emit(str(success))
            self.show_participantdetails()
            self.close()
        else:
            QMessageBox.critical(self, "Error", "DB ERROR")

    def show_selected_date(self, age):
        selected_date = self.date_edit.date().toString(Qt.ISODate)
        self.selected_date_label.setText(selected_date)

    def mousePressEvent(self, event):
        if self.date_edit.underMouse():
            self.date_edit.setGeometry(
                self.date_edit.mapToGlobal(self.date_edit.rect().bottomLeft())
            )
            self.date_edit.show()
        else:
            self.date_edit.hide()
        super().mousePressEvent(event)

    def mousePressEvent(self, event):
        """Event handler for mouse press events."""
        self.mousePress = event.pos()

    def mouseMoveEvent(self, event):
        """Event handler for mouse move events."""
        if self.mousePress is None:
            return
        self.moveWindow = event.globalPos() - self.mousePress
        self.move(self.moveWindow)

    def mouseReleaseEvent(self, event):
        """Event handler for mouse release events."""
        self.mousePress = None
        self.moveWindow = None


class ExistingParticipantDialog(QDialog):
    """A dialog for selecting an existing participant."""
    """Initializes the ExistingparticipantDialog class.

        Args:
            parent (QWidget): The parent widget.
            title (str): The title of the dialog.
        """
    participant_id_generated = pyqtSignal(str)

    def __init__(self, parent=None, title="SEARCH PARTICIPANTS"):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(450, 100, 550, 200)
        # Initialize title bar first
        self.title_bar = TitleBar(self, title)

        # Initialize main layout
        self.main_layout = QVBoxLayout()

        # Add title bar to main layout
        self.main_layout.addWidget(self.title_bar)

        # Add title separator
        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)

        self.id_number_label = QLabel("ID NUMBER :")
        self.id_field = QLineEdit()

        # Connect to database
        self.client = database.get_client()
        self.db = self.client['MRI_PROJECT']
        self.participants_collection = self.db['participants']

        self.main_layout.addWidget(self.id_number_label)
        self.main_layout.addWidget(self.id_field)
        self.submit_button = QPushButton("INITIATE SEARCH")
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.clicked.connect(self.submit)
        self.main_layout.addWidget(self.submit_button)

        self.participant_info = QLabel()
        self.main_layout.addWidget(self.participant_info)

        # Set main layout for the dialog
        self.setLayout(self.main_layout)
        self.participant_details_window = ParticipantDetailsWindow()


        # Apply styles
        self.setStyleSheet("""
               QDialog {
                   background-color: #f8cba8;
               }
               QLabel {
                   color: black;
                   font-weight: bold;
                   background-color: #f8cba8;
               }
               QLineEdit, QComboBox, QDateEdit {
                   background-color: #fbe5d6;
                   border: 1px solid #c55b26;
                   border-radius: 5px;
                   padding: 3px;
               }
               QPushButton {
                   background-color: #f4b283;
                   color: black;
                   font-weight: bold;
                   border: 1px solid #c55b26;
                   border-radius: 5px;
                   padding: 6px;
               }
               QPushButton:pressed {
                   background-color: #8c3e13;
               }
           """)

    def submit(self):
        """Submits the selected participant ID and emits the generated participant ID signal."""
        participant = database.find_participant(self.id_field.text())
        if participant:
            self.participant_info.setText(
                f"First Name: {participant['first_name']}\nLast Name: {participant['last_name']}\nAge: {participant['age']}\nSex: {participant['sex']}")
            self.participant_id_generated.emit(self.id_field.text())
            self.participant_details_window = ParticipantDetailsWindow()
            self.participant_details_window.show_details(participant)
            self.participant_details_window.show()
            self.close()

        else:
            self.participant_info.setText("participant not found")
    def mousePressEvent(self, event):
        """Event handler for mouse press events."""
        self.mousePress = event.pos()

    def mouseMoveEvent(self, event):
        """Event handler for mouse move events."""
        if self.mousePress is None:
            return
        self.moveWindow = event.globalPos() - self.mousePress
        self.move(self.moveWindow)

    def mouseReleaseEvent(self, event):
        """Event handler for mouse release events."""
        self.mousePress = None
        self.moveWindow = None


class NoteDialog(CustomDialog):
    """A dialog for displaying and editing a note."""

    def __init__(self, note, parent=None, title="Note"):
        """Initializes the NoteDialog class.

        Args:
            note (str): The initial text of the note.
            parent (QWidget): The parent widget.
            title (str): The title of the dialog.
        """
        super().__init__(parent, title)
        self.note_text_edit = QTextEdit()
        self.note_text_edit.setMinimumSize(300, 200)
        self.note_text_edit.setText(note)
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.main_layout.addWidget(self.note_text_edit)
        self.main_layout.addWidget(self.ok_button)

    def get_note(self):
        """Returns the text of the note.

        Returns:
            str: The text of the note.
        """
        return self.note_text_edit.toPlainText()


class TestHistoryWindow(FramelessWindow):
    """A window for displaying the test history of a participant."""

    def __init__(self, test_data, db, participant_id):
        """Initializes the TestHistoryWindow class.

        Args:
            test_data (list): A list of dictionaries representing the test data.
            db: The database reference.
            participant_id (str): The ID of the participant.
        """
        super().__init__(title="Test History")
        self.test_data = test_data
        self.db = db
        self.participant_id = participant_id
        self.init_ui()

    def init_ui(self):
        """Initializes the user interface of the window."""
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Test #', 'Date', 'Movement #', 'Test', 'MRI', 'Note'])
        self.table.resizeColumnsToContents()

        if self.test_data:
            self.test_data = list(self.test_data)
            self.table.setRowCount(len(self.test_data))

            self.simulation_result_comboboxes = [QComboBox() for _ in self.test_data]
            self.mri_test_result_comboboxes = [QComboBox() for _ in self.test_data]
            self.note_buttons = [QPushButton("View") for _ in self.test_data]

            for i, data in enumerate(self.test_data):
                self.table.setItem(i, 0, QTableWidgetItem(str(data['test_id'])))
                timestamp = datetime.fromisoformat(str(data['timestamp']))
                formatted_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                self.table.setItem(i, 1, QTableWidgetItem(formatted_timestamp))
                self.table.setItem(i, 2, QTableWidgetItem(str(data['movement_amount'])))

                # Test Result column
                cb = self.simulation_result_comboboxes[i]
                cb.addItems(['Failed', 'Passed'])
                cb.setCurrentText(data['test_result'])
                cb.currentTextChanged.connect(self.handle_combobox_text_changed)
                self.table.setCellWidget(i, 3, cb)

                # MRI Result column
                cb = self.mri_test_result_comboboxes[i]
                cb.addItems(['Failed', 'Passed'])
                cb.setCurrentText(data['mri_result'])
                cb.currentTextChanged.connect(self.handle_combobox_text_changed)
                self.table.setCellWidget(i, 4, cb)

                button = self.note_buttons[i]
                button.clicked.connect(self.handle_note_button_clicked)
                self.table.setCellWidget(i, 5, button)

            # Adjust column width to content
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.layout.addWidget(self.table)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.setMinimumSize(680, 600)

    def handle_combobox_text_changed(self, text):
        """Handles the text changed event of the comboboxes.

        Args:
            text (str): The new text of the combobox.
        """
        sender = self.sender()
        if sender in self.simulation_result_comboboxes:
            index = self.simulation_result_comboboxes.index(sender)
            column = 3
        else:
            index = self.mri_test_result_comboboxes.index(sender)
            column = 4

        self.db.update_test_result(self.participant_id, index + 1, self.table.cellWidget(index, 3).currentText(),
                                   self.table.cellWidget(index, 4).currentText())

    def handle_note_button_clicked(self):
        """Handles the click event of the note buttons."""
        sender = self.sender()
        index = self.note_buttons.index(sender)
        note = self.test_data[index].get('note', '')
        note_dialog = NoteDialog(note)
        if note_dialog.exec_() == QDialog.Accepted:
            new_note = note_dialog.get_note()
            self.db.update_note(self.participant_id, index + 1, new_note)

            # Update the note in the table immediately
            self.test_data[index]['note'] = new_note
            self.table.cellWidget(index, 5).setText("View")


class MainWindow(FramelessWindow):
    """
    The main window class for the Mock MRI Scanner application.

    Attributes:
        client: The MongoClient object for database operations.
        db: The MovementData object for interacting with the 'movement_data' collection in the database.
        current_test_data: A list to store the current test data.
        collect_movement_data: A boolean flag indicating whether to collect movement data.
        movement_count: The count of detected movements.
        sound_loader: The SoundLoader object for loading and playing sounds.
        sound_channel: The Pygame sound channel for controlling sound playback.
        participant_details_window: The instance of the participantDetailsWindow.
        participant_id: The ID of the selected participant.
        microphone: The MicrophoneRecorder object for recording audio.

    Methods:
        on_sound_loaded: Callback method when the sound is loaded.
        init_ui: Initializes the user interface of the main window.
        create_controls: Creates the buttons and other controls.
        position_controls: Positions the controls in the layout.
        connect_signals: Connects the signals to their respective slot methods.
        show_participant_details: Displays the participant details window.
        handle_participant_id: Handles the received participant ID.
        start_test: Starts collecting movement data.
        stop_test: Stops collecting movement data and saves the test data to the database.
        show_test_history: Displays the test history window.
        show_microphone_error_message: Shows an error message related to the microphone.
        display_results: Displays the test results.
        toggle_sound: Toggles the sound playback.
        adjust_volume: Adjusts the sound volume.
        toggle_microphone: Toggles the microphone recording.
        closeEvent: Overrides the close event of the main window.
    """

    def __init__(self):
        """Initializes the MainWindow class."""
        super().__init__(title="Mock MRI Scanner")
        self.init_ui()
        self.client = database.get_client()
        db = self.client['MRI_PROJECT']
        movement_data_collection = db['movement_data']
        self.db = database.MovementData(movement_data_collection)
        self.current_test_data = []
        self.collect_movement_data = False
        self.movement_count = 0
        pygame.mixer.init()
        self.sound_loader = SoundLoader("mrisound.mp3")
        self.sound_loader.sound_loaded.connect(self.on_sound_loaded)
        self.sound_loader.start()
        self.sound_channel = None
        self.participant_details_window = None
        self.participant_id = None
        self.threshold = None
        self.microphone = MicrophoneRecorder()

    def on_sound_loaded(self):
        """Callback method when the sound is loaded."""
        self.sound_checkbox.setEnabled(True)  # Enable the sound checkbox
        self.sound_checkbox.setToolTip("Toggle sound")  # Reset the tooltip

    def init_ui(self):
        """Initializes the user interface of the main window."""
        # Set main window properties
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("Main Window")
        self.setGeometry(100, 100, 600, 700)
        self.setWindowFlags(Qt.FramelessWindowHint)

        main_layout = self.layout
        main_layout.setContentsMargins(10, 0, 10, 10)
        self.optical_flow_app = OpticalFlowApp(self, self)
        main_layout.addWidget(self.optical_flow_app)
        self.viewfinder = QLabel(self)
        self.viewfinder.setStyleSheet("background-color: #2c2f33;")
        self.viewfinder.setFrameShape(QFrame.StyledPanel)
        self.viewfinder.setFrameShadow(QFrame.Raised)
        self.viewfinder.setScaledContents(True)
        self.viewfinder.setAlignment(Qt.AlignCenter)
        self.viewfinder.lower()
        main_layout.addWidget(self.viewfinder)

        # Create other widgets and components
        self.create_controls()

        # Add controls to the layout
        controls_layout = QGridLayout()
        controls_layout.setSpacing(2)
        controls_layout.setHorizontalSpacing(10)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(controls_layout)

        # Position controls as required
        self.position_controls(controls_layout)
        self.connect_signals()

        self.show()

    def create_controls(self):
        """Creates the buttons and other controls."""
        self.participant_details_button = self.create_button("participant Details")
        self.start_test_button = self.create_button("Start Test")
        self.stop_test_button = self.create_button("Stop Test")
        self.test_history_button = self.create_button("Test History")
        self.display_results_button = self.create_button("Display Results")
        self.sound_checkbox = QCheckBox()
        self.sound_label = QLabel("Sound🔊")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_label_text = QLabel("Volume")
        self.volume_label_value = QLabel("50%")
        self.toggle_microphone_checkbox = QCheckBox()
        self.toggle_microphone_label = QLabel("Toggle Microphone🎙️")
        self.sensitivity_menu = QComboBox()
        self.sensitivity_label = QLabel("Movement Sensitivity:")
        self.movement_detected_result_label = QLabel("No")
        self.movement_value_label = QLabel("Movement Value:")
        self.movement_detected_label = QLabel("Movement Detected:")
        self.movement_details_label = QLabel("Movement Details")
        self.participant_id_label = QLabel("participant ID: N/A")
        self.sound_simulation_label = QLabel("Sound Simulation")
        self.participant_id_label.setFont(QFont('Roboto', 12, QFont.Bold, italic=True))
        self.spacerline = QFrame()
        self.spacerline.setFrameShape(QFrame.HLine)
        self.spacerline.setFrameShadow(QFrame.Sunken)
        self.spacerline.setLineWidth(10)
        self.spacerline.setStyleSheet("color: #2c2f33;")
        self.empty_label = QLabel()
        self.empty_field = QLabel()
        self.sound_checkbox.setEnabled(False)
        self.sound_checkbox.setToolTip("Loading sound, please wait...")
        self.participant_details_button.setIcon(QIcon("human-icon-png-1904.png"))
        self.start_test_button.setIcon(QIcon("play.png"))
        self.stop_test_button.setIcon(QIcon("Pause.png"))
        self.test_history_button.setIcon(QIcon("fd.png"))
        self.display_results_button.setIcon(QIcon("fs.png"))
        self.display_results_button.setStyleSheet("font-size: 11px;")
        self.movement_details_label.setFont(QFont('Roboto', 12, QFont.Bold, italic=True))
        self.movement_details_label.setStyleSheet("font-size: 12px; text-decoration: underline;")
        self.sound_simulation_label.setFont(QFont('Roboto', 12, QFont.Bold, italic=True))
        self.sound_simulation_label.setStyleSheet("font-size: 12px; text-decoration: underline;")
        self.volume_slider.setFixedWidth(150)
        self.volume_slider.setFixedHeight(10)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)

    def create_button(self, text):
        """Creates a QPushButton with the specified text."""
        button = QPushButton(text, self)
        button.setFont(QFont('Roboto', 12))
        button.setStyleSheet("font-size: 12px;")
        button.setFixedWidth(150)
        return button

    def position_controls(self, layout):
        """Positions the controls in the layout."""
        # Create a QVBoxLayout to stack the buttons vertically
        buttons_layout = QVBoxLayout()

        buttons_layout.addWidget(self.participant_details_button)
        buttons_layout.addWidget(self.start_test_button)
        buttons_layout.addWidget(self.stop_test_button)
        buttons_layout.addWidget(self.test_history_button)
        buttons_layout.addWidget(self.display_results_button)

        movement_layout = QFormLayout()
        movement_layout.setVerticalSpacing(3)
        movement_layout.setHorizontalSpacing(5)
        movement_layout.addRow(self.participant_id_label)
        movement_layout.addRow(self.spacerline)
        movement_layout.addRow(self.movement_details_label)
        movement_layout.addRow(self.movement_detected_label, self.movement_detected_result_label)
        movement_layout.addRow(self.movement_value_label)
        movement_layout.addRow(self.spacerline)

        # Adjust the sound layout
        sound_layout = QVBoxLayout()
        sound_layout.setSpacing(0)
        sound_layout.setContentsMargins(0, 0, 0, 0)
        sound_label_layout = QHBoxLayout()
        sound_label_layout.setSpacing(2)
        sound_label_layout.setContentsMargins(0, 0, 0, 0)
        self.sound_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.sound_checkbox.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        sound_label_layout.addWidget(self.sound_label)
        sound_label_layout.addWidget(self.sound_checkbox)

        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(2)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        self.volume_label_text.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.volume_slider.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.volume_label_value.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        slider_layout.addWidget(self.volume_label_text)
        slider_layout.addWidget(self.volume_slider)
        slider_layout.addWidget(self.volume_label_value)

        microphone_layout = QHBoxLayout()
        microphone_layout.setSpacing(2)
        microphone_layout.setContentsMargins(0, 0, 0, 0)
        self.toggle_microphone_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.toggle_microphone_checkbox.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        microphone_layout.addWidget(self.toggle_microphone_label)
        microphone_layout.addWidget(self.toggle_microphone_checkbox)

        sound_layout.addWidget(self.empty_label)
        sound_layout.addWidget(self.sound_simulation_label)
        sound_layout.addLayout(sound_label_layout)
        sound_layout.addLayout(slider_layout)
        sound_layout.addLayout(microphone_layout)

        layout.addLayout(buttons_layout, 0, 0, 5, 1)
        layout.addLayout(movement_layout, 0, 1, 6, 2)
        layout.addLayout(sound_layout, 2, 1, 3, 1)
        layout.setHorizontalSpacing(10)

    def connect_signals(self):
        """Connects the signals to their respective slot methods."""
        self.participant_details_button.clicked.connect(self.show_participant_details)
        self.start_test_button.clicked.connect(self.start_test)
        self.stop_test_button.clicked.connect(self.stop_test)
        self.test_history_button.clicked.connect(self.show_test_history)
        self.display_results_button.clicked.connect(self.display_results)
        self.sound_checkbox.stateChanged.connect(self.toggle_sound)
        self.volume_slider.valueChanged.connect(self.adjust_volume)
        self.toggle_microphone_checkbox.stateChanged.connect(self.toggle_microphone)

    def show_participant_details(self):
        """Displays the participant details window."""
        self.participant_details_window = ParticipantDetailsWindow()
        self.participant_details_window.participant_id_received.connect(self.handle_participant_id)
        self.participant_details_window.show()

    def handle_participant_id(self, participant_id):
        """Handles the received participant ID."""
        self.participant_id = participant_id
        self.participant_id_label.setText(f"participant ID: {self.participant_id}")  # Update the label
        print(f"Received participant ID: {self.participant_id}")

    def start_test(self):
        """Starts collecting movement data."""
        if self.participant_id is not None:
            self.collect_movement_data = True
            self.movement_count = 0
            self.threshold = None
            print("Started collecting movement data")
        else:
            QMessageBox.critical(self, "Error", "No participant ID selected.")

    def stop_test(self):
        """Stops collecting movement data and saves the test data to the database."""
        self.collect_movement_data = False
        print("Stopped collecting movement data")

        if self.current_test_data:
            for data in self.current_test_data:
                data["participant_id"] = self.participant_id

            self.db.save_test_data(self.current_test_data, self.participant_id)

    def show_test_history(self):
        """Displays the test history window."""
        if self.participant_id is not None:
            test_data = self.db.get_participant_data(self.participant_id)
            if test_data:  # check if test_data is not empty
                self.test_history_window = TestHistoryWindow(test_data, self.db, self.participant_id)
                self.test_history_window.show()
            else:  # if test_data is empty, show a message box
                QMessageBox.information(self, "Info", "The participant history is empty.")
        else:
            QMessageBox.critical(self, "Error", "No participant ID selected.")

    def show_microphone_error_message(self, message):
        """Shows an error message related to the microphone."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Error")
        msg.setInformativeText(message)
        msg.setWindowTitle("Error")
        msg.exec_()

    def display_results(self):
        """Displays the test results."""
        if self.participant_id is not None and self.movement_count is not None:
            QMessageBox.information(self, "Test Results",
                                    f"The participant moved {self.movement_count} times during the simulation")
        else:
            QMessageBox.critical(self, "Error", "No test data available.")

    def toggle_sound(self, state):
        """Toggles the sound playback."""
        if state:
            if self.sound_channel is None and self.sound_loader.sound:
                self.sound_channel = pygame.mixer.find_channel()
                if self.sound_channel:
                    self.sound_channel.set_volume(self.volume_slider.value() / 100)
                    self.sound_channel.play(self.sound_loader.sound, loops=-1)
        else:
            if self.sound_channel:
                self.sound_channel.stop()
                self.sound_channel = None

    def adjust_volume(self, value):
        """Adjusts the sound volume."""
        if self.sound_channel:
            self.sound_channel.set_volume(value / 100)
        self.volume_label_value.setText(f"{value}%")

    def toggle_microphone(self, state):
        """Toggles the microphone recording."""
        if self.microphone.is_microphone_ready():
            if state:
                self.microphone.start()
            else:
                self.microphone.stop()
        else:
            self.show_error_message("No Microphone detected, please connect one and click again.")

    def closeEvent(self, event):
        """Overrides the close event of the main window."""
        if self.microphone.recording:
            self.microphone.stop()
            self.microphone.close()
        self.client.close()
        self.optical_flow_app.close()
        event.accept()




if __name__ == '__main__':
    App = QApplication(sys.argv)
    qt_material.apply_stylesheet(App, theme='dark_orange.xml')
    window = MenuWindow()
    sys.exit(App.exec_())
