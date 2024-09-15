import unittest
from unittest.mock import patch

import numpy as np
from PyQt5.QtWidgets import QWidget, QApplication

from RMI_Simulator.MRI_Test import OpticalFlowApp

# Ensure that a QApplication exists
app = QApplication([])


class TestOpticalFlowApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.app = app

    def setUp(self):
        parent = None  # or an instance of a QWidget subclass
        parent_widget = QWidget()  # or an instance of a QWidget subclass
        self.optical_flow_app = OpticalFlowApp(parent, parent_widget)

    def test_init(self):
        self.assertIsNotNone(self.optical_flow_app.parent_widget)

    def test_init_capture_thread(self):
        self.assertIsNotNone(self.optical_flow_app.capture_thread)

    def test_init_process_thread(self):
        self.assertIsNotNone(self.optical_flow_app.process_thread)

    @patch.object(OpticalFlowApp, 'movement_detected_result_label')
    @patch.object(OpticalFlowApp, 'movement_value_label')
    @patch.object(OpticalFlowApp, 'mock_movement_detected')
    @patch.object(OpticalFlowApp, 'viewfinder')
    def test_display_frame(self, mock_view_finder, mock_movement_value_label, mock_movement_detected,
                           mock_movement_detected_result_label):
        frame = np.zeros((10, 10, 3))
        mock_movement_value = False
        mock_movement_value = 0.0

        self.optical_flow_app.display_frame(frame, mock_movement_detected, mock_movement_value)

        mock_movement_value_label.setText.assert_called_once_with(f"Movement Value: {mock_movement_value:.2f}")
        if not mock_movement_detected:
            mock_movement_detected_result_label.setText.assert_called_once_with("NO Movement Detected")
        else:
            mock_movement_detected_result_label.setText.assert_called_once_with("Movement Detected!")

    @patch.object(OpticalFlowApp, 'process_optical_flow')
    def test_process_frame(self, mock_process_optical_flow):

        frame = np.zeros((10, 10, 3))
        self.optical_flow_app.process_thread.input_frame = frame

        self.optical_flow_app.process_thread.process_frame(frame)

        mock_process_optical_flow.assert_called_once_with(frame, None)

    @patch('RMI_Simulator.RMI_Test.CaptureThread')
    def test_mapping(self, mock_capture_thread):
        parent = None
        parent_widget = QWidget()  # instantiate the needed parent_widget object here
        self.optical_flow_app = OpticalFlowApp(parent, parent_widget)
        self.assertIsNotNone(self.optical_flow_app.capture_thread)


# Running the tests
if __name__ == "__main__":
    unittest.main()
