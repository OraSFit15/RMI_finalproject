import unittest
from unittest.mock import patch, MagicMock

class TestMainInitialization(unittest.TestCase):

    @patch('PyQt5.QtWidgets.QApplication')
    def test_main_initialization(self, MockQApplication):
        # Create a MagicMock instance to represent QApplication
        MockApp = MagicMock()
        MockQApplication.return_value = MockApp

        # Import the correct module and call the correct function
        import RMI_Simulator.Main
        RMI_Simulator.Main.main()  # Adjust this to the correct function

        # Check if QApplication was called
        MockQApplication.assert_called_once()

if __name__ == '__main__':
    unittest.main()
