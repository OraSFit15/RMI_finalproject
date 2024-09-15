import unittest
from PyQt5.QtWidgets import QApplication, QMessageBox
from RMI_Simulator.Login import Login
from PyQt5.QtCore import Qt, QPoint
from unittest.mock import patch, MagicMock

class TestLogin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up the QApplication for the tests."""
        cls.app = QApplication([])

    def setUp(self):
        """Initialize the Login window before each test."""
        self.login = Login()

    def test_login_window_initialization(self):
        """Test that the Login window is initialized correctly."""
        self.assertTrue(self.login.windowFlags() & Qt.FramelessWindowHint)
        self.assertEqual(self.login.username_input.text(), "")
        self.assertEqual(self.login.password_input.text(), "")

    def test_login_button_clicked(self):
        """Test the login button click event."""
        with patch('RMI_Simulator.Login.database.Users.check_user', return_value=True):
            self.login.username_input.setText("test_user")
            self.login.password_input.setText("test_pass")
            self.login.login_clicked()
            self.assertIsNotNone(self.login.main)
            self.assertFalse(self.login.isVisible())

        with patch('RMI_Simulator.Login.database.Users.check_user', return_value=False):
            self.login.username_input.setText("test_user")
            self.login.password_input.setText("wrong_pass")
            with patch.object(QMessageBox, 'about') as mock_about:
                self.login.login_clicked()
                mock_about.assert_called_once_with(self.login, "Error", "Wrong username or password")

    def test_mouse_press_event(self):
        """Test the mouse press event."""
        mock_event = MagicMock()
        mock_event.pos.return_value = QPoint(10, 10)
        self.login.mousePressEvent(mock_event)
        self.assertEqual(self.login.mousePress, QPoint(10, 10))

    def test_mouse_move_event(self):
        """Test the mouse move event."""
        mock_event = MagicMock()
        self.login.mousePress = QPoint(10, 10)
        mock_event.globalPos.return_value = QPoint(20, 20)
        self.login.mouseMoveEvent(mock_event)
        self.assertEqual(self.login.moveWindow, QPoint(10, 10))
        self.assertEqual(self.login.pos(), self.login.moveWindow)

    def test_mouse_release_event(self):
        """Test the mouse release event."""
        self.login.mousePress = QPoint(10, 10)
        self.login.mouseReleaseEvent(None)
        self.assertIsNone(self.login.mousePress)
        self.assertIsNone(self.login.moveWindow)

    @classmethod
    def tearDownClass(cls):
        """Tear down the QApplication after all tests."""
        cls.app.quit()

if __name__ == '__main__':
    unittest.main()
