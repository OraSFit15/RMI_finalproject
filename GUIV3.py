import sys
import datetime
from PyQt5.QtCore import QObject
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
from database import MongoDB
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

db = MongoDB('MRI_PROJECT',['USERS', 'PARTICIPANTS', 'MOVEMENT_DATA'])

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
        self.viewfinder.setGeometry(600, 600, 200, 220)
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
        viewfinder_width = 200
        viewfinder_height = 220
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
        self.title_separator.setStyleSheet("background-color: #f8cba8;")

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

        self.setStyleSheet("""
            .TitleButton {
                background-color: #f4b283;
                color: black;
                font-weight: bold;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 6px;
            }

    
            .TitleButton:pressed {
                background-color: #8c3e13;

            }
        """)

    def clickedEvent(self):
        """Handles the button's click event."""
        if self.text() == "X":
            self.parent.parent.close()
        elif self.text() == "-":
            self.parent.parent.showMinimized()


class Login(QWidget):
    """The login window for the Mock MRI Scanner application."""

    def __init__(self, parent=None, title="MOCK MRI SCANNER"):
        """Initializes the Login class."""
        super().__init__(parent)

        # Create a main layout for the window
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.title_bar = TitleBar(self, title)
        self.password_input = None
        self.appline = None
        self.appname = None
        self.password = None
        self.height = None
        self.width = None
        self.left = None
        self.top = None
        self.login = None
        self.username_input = None
        self.username = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.init_ui()
        self.init_geometry()
        self.client = database.get_client()
        self.db = self.client["MRI_PROJECT"]
        self.user_collection = self.db["USERS"]
        self.users = database.Users(self.user_collection)

        # Create a container widget and its layout for the content
        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setAlignment(Qt.AlignCenter)  # Align the content to the center
        self.container.setLayout(self.container_layout)

        # Add the title bar and container to the main layout
        self.main_layout.addWidget(self.title_bar)
        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)
        self.main_layout.addWidget(self.container)

        # Initialize other UI elements
        self.init_appname()
        self.init_appline()
        self.init_username()
        self.init_password()
        self.init_login_button()

        self.show()

    def init_ui(self):
        """Initializes the user interface of the Login window."""
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("Login")

    def init_geometry(self):
        """Sets up the initial geometry of the Login window."""
        self.top = 450
        self.left = 100
        self.width = 550
        self.height = 200
        self.setGeometry(self.top, self.left, self.width, self.height)
        self.setStyleSheet("""background-color: #f8cba8; """)

    def init_login_button(self):
        """Initializes the Login button."""
        self.login = QPushButton("LOGIN")
        self.login.setFont(QFont('Roboto', 12))
        self.login.setStyleSheet(
            """ QPushButton {""""""
                background-color: #f4b283;
                color: black;
                font-weight: bold;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:pressed {
                background-color: #8c3e13;
            }""")
        self.login.setFixedSize(100, 30)
        self.login.setCursor(Qt.PointingHandCursor)
        self.login.clicked.connect(self.login_clicked)

        self.container_layout.addWidget(self.login)  # Ajouté au layout du conteneur

    def init_username(self):
        """Initializes the Username label and input field."""
        self.username = QLabel("USERNAME:")
        self.username.setStyleSheet(""" color: black;
                       font-weight: bold;
                       background-color: #f8cba8;""")
        self.username_input = QLineEdit()
        self.username_input.setFixedSize(250, 20)
        self.username_input.setStyleSheet(""" color: black;
                font-weight: bold;
                background-color: #f8cba8;""")
        self.username_input.setStyleSheet("""background-color: #fbe5d6;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 3px;""")

        self.container_layout.addWidget(self.username)  # Ajouté au layout du conteneur
        self.container_layout.addWidget(self.username_input)  # Ajouté au layout du conteneur

    def init_password(self):
        """Initializes the Password label and input field."""
        self.password = QLabel("PASSWORD:")
        self.password.setStyleSheet(""" color: black;
                       font-weight: bold;
                       background-color: #f8cba8;""")
        self.password_input = QLineEdit()
        self.password_input.setFixedSize(250, 20)
        self.password_input.setStyleSheet(""" color: black;
                font-weight: bold;
                background-color: #f8cba8;""")
        self.password_input.setStyleSheet("""background-color: #fbe5d6;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 3px;""")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.container_layout.addWidget(self.password)  # Ajouté au layout du conteneur
        self.container_layout.addWidget(self.password_input)  # Ajouté au layout du conteneur

    def init_appname(self):
        """Initializes the application name label."""
        self.appname = QLabel("Welcome, insert your credentials to continue")  # Correction apportée ici
        self.appname.setFont(QFont('Roboto', 12))
        self.appname.setStyleSheet("font-size: 20px;")
        self.container_layout.addWidget(self.appname)  # Ajouté au layout du conteneur

    def init_appline(self):
        """Initializes the horizontal lines below the labels and input fields."""
        self.appline = QFrame()
        self.appline.setGeometry(100, 180, 300, 2)
        self.appline.setStyleSheet("background-color: #f8cbad;")
        self.appline2 = QFrame()
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


class MenuWindow(FramelessWindow):
    def __init__(self):
        """Initializes the Login class."""
        super().__init__(title="Mock MRI Scanner")
        self.stat = None
        self.set = None
        self.exs = None
        self.new = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.label = QLabel("Movement Monitor MRI", self)
        self.label.setGeometry(135, 50, 100, 50)
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
        self.statistics = Statistic()
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

    def show_statistics(self):
        self.statistics.show()
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
        self.stat.clicked.connect(self.show_statistics)
        self.stat.clicked.connect(self.close_window)
        # self.stat.clicked.connect(self.login_clicked)

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
        # self.login.clicked.connect(self.login_clicked)


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
        self.moveWindow = None
        self.mousePress = None
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
        self.submit_button_side.clicked.connect(self.handle_additional_information_button_clicked)


        # Créer un layout horizontal pour la ligne des boutons
        self.button_layout_1 = QHBoxLayout()
        self.button_layout_2 = QHBoxLayout()

        self.hist_anx = QPushButton("HISTORY\nOF ANXIETY LEVEL\nCHANGES")
        self.hist_anx.setCursor(Qt.PointingHandCursor)
        self.button_layout_1.addWidget(self.hist_anx)
        self.hist_anx.setFixedSize(150, 65)

        self.hist_mri = QPushButton("HISTORY\nOF\nMRI TEST")
        self.hist_mri.setCursor(Qt.PointingHandCursor)
        self.hist_mri.clicked.connect(self.show_test_history)
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
        self.test.clicked.connect(self.begin_test)
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

    def show_details(self, participant_details, participant_id):
        """Affiche les détails du participant dans la fenêtre."""
        self.first_name_field.setText(f" {participant_details['first_name']}")
        self.last_name_field.setText(f" {participant_details['last_name']}")
        self.age_field.setText(f" {participant_details['age']}")
        self.id_field.setText(f" {participant_id}")
        self.level_anxiety_field.setText(f" {participant_details['level_anxiety']}")
        self.email_field.setText(f" {participant_details['email']}")
        self.birthdate_field.setText(f" {participant_details['birthdate']}")
        self.gender_field.setText(f" {participant_details['sex']}")

    def show_test_history(self, participant_id):
        """Displays the test history window."""
        if participant_id is not None:
            movement_data_handler = MovementData(
                db.collections['MOVEMENT_DATA'])
            test_data = movement_data_handler.get_participant_data(participant_id)
            if test_data:
                self.test_history_window = TestHistoryWindow(test_data, db,
                                                             participant_id)
                self.test_history_window.show()
            else:
                QMessageBox.information(self, "Info", "The participant history is empty.")
        else:
            # Affiche un message d'erreur si aucun ID de participant n'est sélectionné
            QMessageBox.critical(self, "Error", "No participant ID selected.")

    def handle_participant_id(self, participant_id):
        """Handles the participant ID received from the caller.

        Args:
            participant_id (str): The ID of the selected participant.
        """
        participant = database.find_participant(participant_id)
        if participant:
            participant_details_window = ParticipantDetailsWindow()
            participant_details_window.show_details(participant, participant_id)  # Passer participant_id
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

    def closeEvent(self, event):
        menuWindow = MenuWindow()
        menuWindow.show()

    def handle_additional_information_button_clicked(self):
        """Handles the click event of the additional information button."""
        button_clicked = self.sender()
        if button_clicked == self.submit_button_side:
            note_dialog = NoteDialog(note="")
            note_dialog.exec_()

    def begin_test(self):
        """Starts the test """
        begin_test = MainWindow()
        begin_test.show()
class NewParticipantDialog(QDialog):
    """A dialog for entering information about a new participant."""
    participant_id_generated = pyqtSignal(str)

    def __init__(self, parent=None, title="NEW PARTICIPANT FORM"):
        super().__init__(parent)
        self.mousePress = None
        self.moveWindow = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(450, 100, 550, 200)

        # Initialize main layout
        self.main_layout = QVBoxLayout()

        # Add title bar to main layout
        self.title_bar = TitleBar(self, title)
        self.main_layout.addWidget(self.title_bar)

        self.label_email = QLabel("Email:")
        self.email_field = QLineEdit()
        email_validator = QRegularExpressionValidator(QRegularExpression(r'^[\w\.-]+@[\w\.-]+\.\w+$'))
        self.email_field.setValidator(email_validator)
        self.label_level_anxiety = QLabel("Level of Anxiety:")
        self.level_anxiety_field = QLineEdit()
        validator_level = QIntValidator(0, 90)
        self.level_anxiety_field.setValidator(validator_level)
        self.contact_number_label = QLabel("Contact Number")
        self.contact_number_field = QLineEdit()
        validator_nb = QIntValidator(0, 999999999)
        self.contact_number_field.setValidator(validator_nb)
        self.submit_button_side = QPushButton("ADDITIONAL INFORMATION")
        self.submit_button_side.setCursor(Qt.PointingHandCursor)
        self.first_name_field = QLineEdit()
        self.last_name_field = QLineEdit()
        self.id_number_label = QLabel("Id Number:")
        self.id_number_field = QLineEdit()
        validator_id = QIntValidator(0, 999999999)
        self.id_number_field.setValidator(validator_id)
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
        self.submit_button_side.clicked.connect(self.handle_additional_information_button_clicked)

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

    def submit(self):
        # Vérifiez si tous les champs requis sont remplis
        if self.first_name_field.text() == '' or self.last_name_field.text() == '':
            QMessageBox.warning(self, "Warning", "Please fill in all required fields.")
            return

        # Obtenez la date de naissance sélectionnée et calculez l'âge
        selected_date = self.date_edit.date().toPyDate()
        selected_date_str = selected_date.strftime("%Y-%m-%d")
        self.selected_date_label.setText(selected_date_str)
        selected_date = datetime.datetime(selected_date.year, selected_date.month, selected_date.day)
        current_date = datetime.datetime.now()
        age = current_date.year - selected_date.year - (
                    (current_date.month, current_date.day) < (selected_date.month, selected_date.day))

        if age < 0:
            QMessageBox.warning(self, "Warning", "Invalid date of birth.")
            return

        id_number = self.id_number_field.text()
        if not id_number.isdigit() or len(id_number) != 9:
            QMessageBox.warning(self, "Warning", "Invalid ID number. Please enter a 9-digit number.")
            return

        level = self.level_anxiety_field.text()
        if not level.isdigit() or len(level) not in (1, 2):
            QMessageBox.warning(self, "Warning", "Level number please enter a number from 0 to 10")
            return

        phone_number = self.contact_number_field.text()
        if not phone_number.isdigit() or len(phone_number) != 9:
            QMessageBox.warning(self, "Warning", "Invalid phone number. Please enter a 10-digit number.")
            return

        if not self.email_field.hasAcceptableInput():
            QMessageBox.warning(self, "Warning", "Invalid email address.")
            return

        # Si toutes les validations sont réussies, insérez les données dans la base de données
        success = database.insert_participant(
            self.first_name_field.text(),
            self.last_name_field.text(),
            self.sex_field.currentText(),
            id_number,
            selected_date_str,
            age,
            self.email_field.text(),
            phone_number,
            self.level_anxiety_field.text(),
        )

        if success:
            self.participant_id_generated.emit(str(success))
            self.close()
        else:
            QMessageBox.critical(self, "Error", "DB ERROR")

    def show_selected_date(self, age):
        selected_date = self.date_edit.date().toString(Qt.ISODate)
        self.selected_date_label.setText(selected_date)

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

    def closeEvent(self, event):
        menuWindow = MenuWindow()
        menuWindow.show()

    def handle_additional_information_button_clicked(self):
        """Handles the click event of the additional information button."""
        button_clicked = self.sender()
        if button_clicked == self.submit_button_side:
            note_dialog = NoteDialog(note="")
            note_dialog.exec_()

class Statistic(QDialog):
    """A window for displaying statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statistics")
        self.setGeometry(450, 100, 550, 200)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.add_stat = AdditionalStat()
        # Main layout
        main_layout = QVBoxLayout()

        # Title bar
        title_bar = TitleBar(self, "STATISTICS")
        main_layout.addWidget(title_bar)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: orange;")
        main_layout.addWidget(separator)

        # Fields layout
        fields_layout = QGridLayout()

        # Number of participants
        num_participants_label = QLabel("Number of Participants:")
        num_participants_field = QLineEdit()
        fields_layout.addWidget(num_participants_label, 0, 0)
        fields_layout.addWidget(num_participants_field, 0, 1)

        # Gender distribution
        gender_label = QLabel("Gender Distribution:")
        female_field = QLineEdit()
        female_field.setPlaceholderText("Female")
        male_field = QLineEdit()
        male_field.setPlaceholderText("Male")
        other_field = QLineEdit()
        other_field.setPlaceholderText("Other")
        fields_layout.addWidget(gender_label, 1, 0)
        fields_layout.addWidget(female_field, 1, 1)
        fields_layout.addWidget(male_field, 1, 2)
        fields_layout.addWidget(other_field, 1, 3)

        # Average age
        average_age_label = QLabel("Average Age:")
        average_age_field = QLineEdit()
        average_from_label = QLabel("From:")
        average_age_from_field = QLineEdit()
        average_to_label = QLabel("To:")
        average_age_to_field = QLineEdit()

        fields_layout.addWidget(average_age_label, 2, 0)
        fields_layout.addWidget(average_age_field, 2, 1)
        fields_layout.addWidget(average_from_label, 2, 2)
        fields_layout.addWidget(average_age_from_field, 2, 3)
        fields_layout.addWidget(average_to_label, 2, 4)
        fields_layout.addWidget(average_age_to_field, 2, 5)

        average_time_label = QLabel("Average Time:")
        average_time_field = QLineEdit()
        max_time_label = QLabel("Max Time:")
        max_time_field = QLineEdit()
        min_time_label = QLabel("Min Time:")
        min_time_field = QLineEdit()
        fields_layout.addWidget(average_time_label, 3, 0)
        fields_layout.addWidget(average_time_field, 3, 1)
        fields_layout.addWidget(max_time_label, 3, 2)
        fields_layout.addWidget(max_time_field, 3, 3)
        fields_layout.addWidget(min_time_label, 3, 4)
        fields_layout.addWidget(min_time_field, 3, 5)

        # Add fields layout to main layout
        main_layout.addLayout(fields_layout)

        # Additional Stat button
        additional_stat_button = QPushButton("ADDITIONAL STATISTICS")
        additional_stat_button.setCursor(Qt.PointingHandCursor)
        additional_stat_button.clicked.connect(self.show_addstat)
        main_layout.addWidget(additional_stat_button)

        # Set main layout for dialog
        self.setLayout(main_layout)

        # Stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: #f8cba8;
            }
            QLabel {
                color: black;
                font-weight: bold;
                background-color: #f8cba8;
            }
            QLineEdit {
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
    def show_addstat(self):
        """Show add statistics."""
        self.close()
        self.add_stat.show()


class AdditionalStat(QDialog):
    """A window for displaying additional statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Additional Statistics")
        self.setGeometry(450, 100, 550, 200)
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Main layout
        main_layout = QVBoxLayout()

        # Title bar
        title_bar = TitleBar(self, "ADDITIONAL STATISTICS")
        main_layout.addWidget(title_bar)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: orange;")
        main_layout.addWidget(separator)

        # Fields layout
        fields_layout = QGridLayout()

        # Number of participants
        num_participants_label = QLabel("Number of Participants:")
        num_participants_field = QLineEdit()
        fields_layout.addWidget(num_participants_label, 0, 0)
        fields_layout.addWidget(num_participants_field, 0, 1)

        # Gender distribution
        gender_label = QLabel("Gender Distribution:")
        female_field = QLineEdit()
        female_field.setPlaceholderText("Female")
        male_field = QLineEdit()
        male_field.setPlaceholderText("Male")
        other_field = QLineEdit()
        other_field.setPlaceholderText("Other")
        fields_layout.addWidget(gender_label, 1, 0)
        fields_layout.addWidget(female_field, 1, 1)
        fields_layout.addWidget(male_field, 1, 2)
        fields_layout.addWidget(other_field, 1, 3)

        # Average age
        average_age_label = QLabel("Average Age:")
        average_age_field = QLineEdit()
        average_from_label = QLabel("From:")
        average_age_from_field = QLineEdit()
        average_to_label = QLabel("To:")
        average_age_to_field = QLineEdit()

        fields_layout.addWidget(average_age_label, 2, 0)
        fields_layout.addWidget(average_age_field, 2, 1)
        fields_layout.addWidget(average_from_label, 2, 2)
        fields_layout.addWidget(average_age_from_field, 2, 3)
        fields_layout.addWidget(average_to_label, 2, 4)
        fields_layout.addWidget(average_age_to_field, 2, 5)

        # Average time
        average_time_label = QLabel("Average Time:")
        average_time_field = QLineEdit()
        max_time_label = QLabel("Max Time:")
        max_time_field = QLineEdit()
        min_time_label = QLabel("Min Time:")
        min_time_field = QLineEdit()
        fields_layout.addWidget(average_time_label, 3, 0)
        fields_layout.addWidget(average_time_field, 3, 1)
        fields_layout.addWidget(max_time_label, 3, 2)
        fields_layout.addWidget(max_time_field, 3, 3)
        fields_layout.addWidget(min_time_label, 3, 4)
        fields_layout.addWidget(min_time_field, 3, 5)

        # Add fields layout to main layout
        main_layout.addLayout(fields_layout)

        # Additional Stat button


        # Additional buttons
        button_layout = QHBoxLayout()

        button1 = QPushButton("SHOW GRAPHICALLY")
        button1.setCursor(Qt.PointingHandCursor)

        button2 = QPushButton("SAVE AS PDF")
        button2.setCursor(Qt.PointingHandCursor)

        button3 = QPushButton("SAVE TO EXCEL")
        button3.setCursor(Qt.PointingHandCursor)


        button_layout.addWidget(button1)
        button_layout.addWidget(button2)
        button_layout.addWidget(button3)

        main_layout.addLayout(button_layout)

        # Set main layout for dialog
        self.setLayout(main_layout)

        # Stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: #f8cba8;
            }
            QLabel {
                color: black;
                font-weight: bold;
                background-color: #f8cba8;
            }
            QLineEdit {
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
        self.moveWindow = None
        self.mousePress = None
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
        participant_id = self.id_field.text()

        if participant:
            self.participant_info.setText(
                f"First Name: {participant['first_name']}\nLast Name: {participant['last_name']}\nAge: {participant['age']}\nSex: {participant['sex']}")
            self.participant_id_generated.emit(self.id_field.text())
            self.participant_details_window = ParticipantDetailsWindow()
            self.participant_details_window.show_details(participant, participant_id)
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

    def closeEvent(self, event):
        menuWindow = MenuWindow()
        menuWindow.show()


class NoteDialog(QDialog):
    """A dialog for displaying and editing a note."""

    def __init__(self,note="", parent=None, title="ADDITIONAL INFORMATION"):
        """Initializes the NoteDialog class.

        Args:
            parent (QWidget): The parent widget.
            title (str): The title of the dialog.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(450, 100, 550, 200)

        # Initialize main layout
        self.main_layout = QVBoxLayout()

        # Add title bar to main layout
        self.title_bar = TitleBar(self, title)
        self.main_layout.addWidget(self.title_bar)

        # Add QTextEdit for note input
        self.note_text_edit = QTextEdit()
        self.note_text_edit.setMinimumSize(300, 200)
        self.main_layout.addWidget(self.note_text_edit)

        # Add OK button to save note
        self.ok_button = QPushButton("OK")
        self.ok_button.setCursor(Qt.PointingHandCursor)

        self.ok_button.clicked.connect(self.get_note)

        self.main_layout.addWidget(self.ok_button)

        # Set the main layout for the dialog
        self.setLayout(self.main_layout)

        self.setModal(True)  # Set the dialog as modal

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

    def get_note(self):
        """Returns the text of the note.

        Returns:
            str: The text of the note.
        """
        return self.note_text_edit.toPlainText()

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

class TestHistoryWindow(QDialog):
    """A dialog for displaying the test history of a participant."""

    def __init__(self, test_data, db, participant_id,parent=None, title="HISTORY WINDOW"):
        """Initializes the TestHistoryDialog class.

        Args:
            test_data (list): A list of dictionaries representing the test data.
            db: The database reference.
            participant_id (str): The ID of the participant.
        """
        super().__init__()

        self.table = None
        self.main_layout = None
        self.title_bar = None
        self.test_data = test_data
        self.db = db
        self.participant_id = participant_id
        self.init_ui()

    def init_ui(self):
            """Initializes the user interface of the dialog."""
            self.main_layout = QVBoxLayout(self)
            self.setWindowFlags(Qt.FramelessWindowHint)
            self.title_bar = TitleBar(self, "TEST HISTORY")
            self.main_layout.addWidget(self.title_bar)
            self.setGeometry(450, 100, 550, 200)

            # Ajoutez la ligne de séparation de titre
            self.title_separator = QFrame(self)
            self.title_separator.setFrameShape(QFrame.HLine)
            self.title_separator.setFrameShadow(QFrame.Sunken)
            self.title_separator.setStyleSheet("background-color: orange;")
            self.main_layout.addWidget(self.title_separator)

            # Créez et configurez le widget de tableau
            self.table = QTableWidget()
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels(['NUMBER', 'DATE', 'DURATION', 'ACCURACY', 'VOLUME', 'SUCCESS'])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.main_layout.addWidget(self.table)

            # Remplissez le tableau avec les données de test
            self.populate_table()

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

    def populate_table(self):
        """Populates the table widget with test data."""
        if self.test_data:
            self.test_data = list(self.test_data)
            self.table.setRowCount(len(self.test_data))

            for i, data in enumerate(self.test_data):
                self.table.setItem(i, 0, QTableWidgetItem(str(data['test_id'])))
                timestamp = QDateTime.fromSecsSinceEpoch(int(data['timestamp']))
                formatted_timestamp = timestamp.toString(Qt.DefaultLocaleLongDate)
                self.table.setItem(i, 1, QTableWidgetItem(formatted_timestamp))
                self.table.setItem(i, 2, QTableWidgetItem(str(data['movement_amount'])))
                self.table.setItem(i, 3, QTableWidgetItem(data['test_result']))
                self.table.setItem(i, 4, QTableWidgetItem(data['mri_result']))

                # Add note button to cell
                note_button = QPushButton("View")
                note_button.clicked.connect(lambda _, index=i: self.handle_note_button_clicked(index))
                self.table.setCellWidget(i, 5, note_button)

    def handle_note_button_clicked(self, index):
        """Handles the click event of the note buttons."""
        note = self.test_data[index].get('note', '')
        note_dialog = NoteDialog(note)
        if note_dialog.exec_() == QDialog.Accepted:
            new_note = note_dialog.get_note()
            self.db.update_note(self.participant_id, index + 1, new_note)
            self.test_data[index]['note'] = new_note
            self.populate_table()
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

    def closeEvent(self, event):
        self.close()
        if isinstance(self.participant_id, str):
            detailsWindow = ParticipantDetailsWindow(self.participant_id)
            detailsWindow.show()

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
        get_current_date: Get the current date.
        get_current_time: Get the current time.
        update_time: Update the time label.
        closeEvent: Overrides the close event of the main window.
    """

    def __init__(self):
        """Initializes the MainWindow class."""
        super().__init__(title="Examination of the MRI Simulator")  # Modifier le titre de la fenêtre
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
        self.sound_channel = None
        self.sound_loader.sound_loaded.connect(self.toggle_sound)
        self.sound_loader.start()
        self.sound_channel = None
        self.participant_details_window = None
        self.participant_id = None
        self.threshold = None
        self.microphone = MicrophoneRecorder()

    def init_ui(self):
        """Initializes the user interface of the main window."""
        # Set main window properties
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("Main Window")
        self.setGeometry(100, 100, 600, 700)
        self.setWindowFlags(Qt.FramelessWindowHint)

        main_layout = self.layout
        main_layout.setContentsMargins(10, 0, 10, 10)
        self.viewfinder = QLabel(self)
        self.viewfinder.setFrameShape(QFrame.StyledPanel)
        self.viewfinder.setFrameShadow(QFrame.Raised)
        self.viewfinder.setScaledContents(True)
        self.viewfinder.setAlignment(Qt.AlignCenter)
        self.viewfinder.lower()
        main_layout.addWidget(self.viewfinder)

        self.optical_flow_app = OpticalFlowApp(self, self)
        main_layout.addWidget(self.optical_flow_app)

        # Create other widgets and components
        self.create_controls()

        # Add controls to the layout
        controls_layout = QGridLayout()
        controls_layout.setSpacing(2)
        controls_layout.setHorizontalSpacing(10)
        main_layout.addLayout(controls_layout)

        # Position controls as required
        self.position_controls(controls_layout)
        self.connect_signals()
        self.date_label = QLabel(self)
        self.date_label.setText(self.get_current_date())
        self.time_label = QLabel(self)
        self.time_label.setText(self.get_current_time())

        # Layout and styling (optional)
        date_time_layout = QHBoxLayout()
        date_time_layout.addWidget(self.date_label)
        date_time_layout.addWidget(self.time_label)
        date_time_layout.addStretch()  # Add stretch to move labels to the right
        main_layout.addLayout(date_time_layout)

        # Align the date and time labels to the bottom-right corner
        main_layout.addStretch()

        # Update time every second (optional)
        timer = QTimer(self)
        timer.setInterval(1000)  # 1 second
        timer.timeout.connect(self.update_time)
        timer.start()
        self.show()

        self.setStyleSheet("""
                   background-color: #f8cba8;
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

    def create_controls(self):
        """Creates the buttons and other controls."""
        self.start_test_button = self.create_button("START")
        self.stop_test_button = self.create_button("STOP")

        self.start_test_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.stop_test_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        button_width = 100  # Set your desired width
        button_height = 30  # Set your desired height

        self.start_test_button.setFixedSize(button_width, button_height)
        self.stop_test_button.setFixedSize(button_width, button_height)
        self.start_test_button.setCursor(Qt.PointingHandCursor)
        self.stop_test_button.setCursor(Qt.PointingHandCursor)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_label_text = QLabel("VOLUME")
        self.volume_label_value = QLabel("50")
        self.toggle_microphone_checkbox = QCheckBox()
        self.toggle_microphone_label = QLabel("MICROPHONE 🎙️")
        self.sensitivity_menu = QComboBox()
        self.sensitivity_label = QLabel("Movement Sensitivity:")
        self.movement_detected_result_label = QLabel("No")
        self.movement_value_label = QLabel("Movement Value:")
        self.movement_detected_label = QLabel("Movement Detected:")
        self.movement_details_label = QLabel("Movement Details")
        self.spacerline = QFrame()
        self.spacerline.setFrameShape(QFrame.HLine)
        self.spacerline.setFrameShadow(QFrame.Sunken)
        self.spacerline.setLineWidth(10)
        self.spacerline.setStyleSheet("color: #2c2f33;")
        self.empty_label = QLabel()
        self.empty_field = QLabel()
        self.movement_details_label.setFont(QFont('Roboto', 12, QFont.Bold, italic=True))
        self.movement_details_label.setStyleSheet("font-size: 12px; text-decoration: underline;")
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(0)
        self.volume_slider.setTickInterval(5)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_label = QLabel("ALLOWABLE DEVIATION")
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(3)
        self.threshold_slider.setTickInterval(1)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)

        self.volume_slider.setStyleSheet(
            """
            color: white;
            font-weight: bold;

            QSlider::groove:horizontal {
                border: none;  /* Remove border for a seamless look */
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #e0e0e0, stop:1 #cccccc);
                height: 8px;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: #f0f0f0;  /* Lighter handle background */
                border: 1px solid #cccccc;
                width: 13px;  /* Adjust width for a slimmer handle */
                margin: 2px 0;  /* Adjust for vertical centering */
            }

            /* Optional: Add a subtle shadow effect to the handle */
            QSlider::handle:horizontal {
                qproperty-shadow: 0 1px 1px #aaaaaa;
            }
             QLabel {
                       color: black;
                       font-weight: bold;
                       background-color: #f8cba8;
                   }
            """
        )

    def create_button(self, text):
        """Creates a QPushButton with the specified text."""
        button = QPushButton(text, self)
        button.setStyleSheet("""background-color: #f4b283;
                       color: black;
                       font-weight: bold;
                       border: 1px solid #c55b26;
                       border-radius: 5px;
                       padding: 6px;""")
        button.setFixedWidth(150)
        return button

    def position_controls(self, layout):
        """Positions the controls in the layout."""
        # Create a QVBoxLayout to stack the buttons vertically on the left side

        # Adjust the sound layout
        sound_layout = QVBoxLayout()
        sound_layout.setSpacing(0)
        sound_layout.setContentsMargins(0, 0, 0, 0)

        # Sound Label and Slider Layout
        sound_slider_layout = QVBoxLayout()
        sound_slider_layout.addWidget(self.volume_label_value)
        sound_slider_layout.addWidget(self.volume_slider)

        # Microphone Label and Checkbox Layout
        microphone_layout = QVBoxLayout()
        microphone_layout.addWidget(self.toggle_microphone_label)
        microphone_layout.addWidget(self.toggle_microphone_checkbox)

        # Threshold Label and Slider Layout
        threshold_layout = QVBoxLayout()
        threshold_layout.addWidget(self.threshold_label)
        threshold_layout.addWidget(self.threshold_slider)

        # Add each group (label-slider) to sound layout
        sound_layout.addWidget(self.volume_label_text)
        sound_layout.addLayout(sound_slider_layout)
        sound_layout.addLayout(microphone_layout)

        sound_layout.addLayout(threshold_layout)  # Add threshold layout

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.start_test_button)
        buttons_layout.addWidget(self.stop_test_button)
        buttons_layout.addStretch()

        buttons_layout.setSpacing(10)
        layout.setColumnStretch(0, 1)
        # Create a layout for the video widget on the right side
        video_layout = QVBoxLayout()
        video_layout.addWidget(self.viewfinder)  # Add viewfinder to the video layout
        video_layout.addStretch()  # Add stretch to align viewfinder to the top

        # Add controls to the layout
        layout.addLayout(buttons_layout, 1, 0)  # Buttons on the left
        layout.addLayout(sound_layout, 0, 0)  # Sound controls on the left
        layout.addLayout(video_layout, 0, 1, 2, 1)  # Video widget on the right

    def connect_signals(self):
        """Connects the signals to their respective slot methods."""
        self.start_test_button.clicked.connect(self.start_test)
        self.stop_test_button.clicked.connect(self.stop_test)
        self.volume_slider.valueChanged.connect(self.adjust_volume)
        self.toggle_microphone_checkbox.stateChanged.connect(self.toggle_microphone)

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
            self.threshold = self.threshold_slider.value()  # Update threshold value
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

    def show_microphone_error_message(self, message):
        """Shows an error message related to the microphone."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Error")
        msg.setInformativeText(message)
        msg.setWindowTitle("Error")
        msg.exec_()

    def toggle_sound(self):
        """Active ou désactive la lecture du son."""
        state = True  # Mettez ici l'état que vous voulez
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
        self.volume_label_value.setText(f"{value}")

    def toggle_microphone(self, state):
        """Toggles the microphone recording."""
        if self.microphone.is_microphone_ready():
            if state:
                self.microphone.start()
            else:
                self.microphone.stop()
        else:
            self.show_error_message("No Microphone detected, please connect one and click again.")

    def get_current_date(self):
        today = datetime.date.today()
        return today.strftime("%B %d, %Y")  # Format the date (e.g., March 30, 2024)

    def get_current_time(self):
        now = datetime.datetime.now()
        return now.strftime("%H:%M:%S")  # Format the time (e.g., 23:21:00)

    def update_time(self):
        self.time_label.setText(self.get_current_time())

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
