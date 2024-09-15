import unittest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt, QPoint, QEvent
from PyQt5.QtGui import QMouseEvent
from RMI_Simulator.GUI import CustomDialog
from RMI_Simulator.GUI import TitleButton
class TestCustomDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up the application instance."""
        cls.app = QApplication([])

    def setUp(self):
        """Set up the CustomDialog instance for testing."""
        self.dialog = CustomDialog()
        self.dialog.mousePress = None  # Ensure mousePress is initialized
        self.dialog.show()

    def test_dialog_initialization(self):
        """Test if the dialog initializes correctly with the custom title bar."""
        self.assertIsNotNone(self.dialog.title_bar)
        self.assertTrue(self.dialog.windowFlags() & Qt.FramelessWindowHint)

    def test_mouse_press_event(self):
        """Test mouse press event sets the correct position."""
        test_event = QMouseEvent(QEvent.MouseButtonPress, QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.dialog.mousePressEvent(test_event)
        self.assertEqual(self.dialog.mousePress, test_event.pos())

    def test_mouse_move_event_no_press(self):
        """Test mouse move event does nothing when mousePress is None."""
        self.dialog.mouseMoveEvent(None)
        # Nothing to assert, just ensuring no exceptions or errors occur

    def test_mouse_move_event_with_press(self):
        """Test if the dialog moves when the mouse is pressed and moved."""
        initial_position = self.dialog.pos()

        # Simulate mouse press
        test_press_event = QMouseEvent(QEvent.MouseButtonPress, QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.dialog.mousePressEvent(test_press_event)

        # Simulate mouse move
        test_move_event = QMouseEvent(QEvent.MouseMove, QPoint(30, 30), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.dialog.mouseMoveEvent(test_move_event)

        # Check if the window moved
        self.assertNotEqual(self.dialog.pos(), initial_position)

    def test_mouse_release_event(self):
        """Test if mouseReleaseEvent resets mousePress and moveWindow."""
        # Set some initial values
        self.dialog.mousePress = QPoint(10, 10)
        self.dialog.moveWindow = QPoint(20, 20)

        # Simulate mouse release
        test_release_event = QMouseEvent(QEvent.MouseButtonRelease, QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.dialog.mouseReleaseEvent(test_release_event)

        # Ensure the values are reset
        self.assertIsNone(self.dialog.mousePress)
        self.assertIsNone(self.dialog.moveWindow)

    def test_close_button_click(self):
        """Test if the close button closes the parent window."""
        close_button = TitleButton("X", self.dialog.title_bar)

        # Check that the dialog is initially visible
        self.assertTrue(self.dialog.isVisible())

        # Simulate clicking the close button
        QTest.mouseClick(close_button, Qt.LeftButton)

        # After clicking, the dialog should be closed (not visible)
        self.assertFalse(self.dialog.isVisible())

    def test_minimize_button_click(self):
        """Test if the minimize button minimizes the parent window."""
        minimize_button = TitleButton("-", self.dialog.title_bar)

        # Check that the dialog is initially not minimized
        self.assertFalse(self.dialog.isMinimized())

        # Simulate clicking the minimize button
        QTest.mouseClick(minimize_button, Qt.LeftButton)

        # After clicking, the dialog should be minimized
        self.assertTrue(self.dialog.isMinimized())

    def tearDown(self):
        """Clean up after each test."""
        self.dialog.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up the application instance."""
        cls.app.quit()

if __name__ == '__main__':
    unittest.main()
