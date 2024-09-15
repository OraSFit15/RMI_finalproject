import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import cv2
from PyQt5.QtTest import QTest
from queue import Queue
from RMI_Simulator.MRI_Test import CaptureThread
class CaptureThreadWithQueue(CaptureThread):
    """Une version modifiée de CaptureThread pour utiliser une queue."""

    def __init__(self, frame_queue):
        super().__init__()
        self.frame_queue = frame_queue

    def run(self):
        self.running = True
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FPS, 60)

        while self.running:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (704, 576))
                self.frame_queue.put(frame)  # Mettre le frame dans la queue

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()

class TestCaptureThread(unittest.TestCase):

    @patch('cv2.VideoCapture')
    def test_run(self, mock_video_capture):
        """Test the run method of CaptureThread."""

        # Mock the VideoCapture object to simulate camera connection
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, np.zeros((576, 704, 3), dtype=np.uint8))  # Simule une image capturée
        mock_video_capture.return_value = mock_cap

        # Create a queue to receive frames
        frame_queue = Queue()

        # Instantiate the modified CaptureThread
        capture_thread = CaptureThreadWithQueue(frame_queue)

        # Start the thread
        print("Starting the thread...")
        capture_thread.start()
        print("Thread started")

        # Wait for the thread to process (simulate capture delay)
        QTest.qWait(500)  # Augmenter le temps d'attente pour laisser le thread capturer une image

        # Stop the thread
        print("Stopping the thread...")
        capture_thread.stop()
        capture_thread.wait()
        print("Thread stopped")

        # Check if a frame was added to the queue
        print("Queue size:", frame_queue.qsize())
        self.assertFalse(frame_queue.empty(), "No frames were captured")

        # Ensure the camera was released
        mock_cap.release.assert_called_once()

        # Ensure the thread stopped running
        self.assertFalse(capture_thread.running)

if __name__ == '__main__':
    unittest.main()
