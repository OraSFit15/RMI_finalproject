import datetime
import threading

import cv2
import numpy as np
import pyaudio
import pygame
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QWidget


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
        self.running = True  # Add a flag to control the thread

    def input_frame_slot(self, frame):
        """Receives input frames from the capture thread.

        Args:
            frame (np.ndarray): The input frame captured by the camera.
        """
        self.input_frame = frame

    def run(self):
        """Starts the thread to process captured frames."""
        while self.running:
            if self.input_frame is not None:
                self.process_frame(self.input_frame)
                self.input_frame = None

    def process_frame(self, frame):
        """Processes the frame using the provided optical flow application.

        Args:
            frame (np.ndarray): The frame to be processed using optical flow.
        """
        # Convert frame to 8-bit if needed
        if frame.dtype == np.float64:
            frame = np.uint8(frame * 255.0)  # Adjust this based on how your frame data is normalized

        # Process the frame
        prev_gray, movement_detected, movement_value = self.optical_flow_app.process_optical_flow(
            frame, self.optical_flow_app.prev_gray
        )

        # Emit the processed frame signal
        self.processed_frame_signal.emit(frame, movement_detected, movement_value)

        # Update previous gray frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.optical_flow_app.prev_gray = gray

    def stop(self):
        """Stops the processing thread."""
        self.running = False


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
            self.parent_widget.movement_detected_result_label.setText("Movement Detected!")
            self.parent_widget.movement_detected_result_label.setStyleSheet("font-size: 12px; color: red;")

            if self.parent_widget.collect_movement_data:
                movement_data = {
                    "movement_detected": movement_detected,
                    "movement_value": movement_value,
                    "timestamp": datetime.datetime.utcnow(),
                }
                self.parent_widget.movement_count += 1
                self.parent_widget.current_test_data.append(movement_data)
        else:
            self.parent_widget.movement_detected_result_label.setText("NO Movement Detected")
            self.parent_widget.movement_detected_result_label.setStyleSheet("font-size: 12px; color: green;")

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
        movement_value = 0.0

        if prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 6, 5, 1.2, 0)
            magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

            if self.parent_widget.threshold is None:
                self.threshold = 3
                self.parent_widget.threshold = self.threshold
                print(f"Threshold: {self.threshold}")
            if not self.threshold:
                self.threshold = np.max(np.mean(magnitude[:500])) + 0.05
            movement_detected = np.mean(magnitude) > self.threshold
            movement_value = float(np.mean(magnitude))

            # Visualization
            hsv = np.zeros((frame.shape[0], frame.shape[1], 3), dtype=np.float32)
            hsv[..., 1] = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[..., 1]
            hsv[..., 0] = 0.5 * 180
            hsv[..., 2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
            color = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        prev_gray = gray
        return prev_gray, movement_detected, movement_value


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
