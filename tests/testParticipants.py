import sys
import unittest
from unittest.mock import patch

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMessageBox

from RMI_Simulator.Participants import NewParticipantDialog, ExistingParticipantDialog


class TestNewParticipantDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)

    def setUp(self):
        self.dialog = NewParticipantDialog(title="NEW PARTICIPANT FORM")
        self.dialog.show()  # Ensure the dialog is visible

    def test_initial_ui_state(self):
        self.assertEqual(self.dialog.windowTitle(), "NEW PARTICIPANT FORM")
        self.assertTrue(self.dialog.submit_button.isEnabled())

    @patch('RMI_Simulator.Participants.database.insert_participant', return_value='123')
    def test_submit_with_valid_data(self, mock_insert):
        self.dialog.first_name_field.setText('John')
        self.dialog.last_name_field.setText('Doe')
        self.dialog.email_field.setText('john.doe@example.com')
        self.dialog.id_number_field.setText('123456789')
        self.dialog.contact_number_field.setText('1234567890')
        self.dialog.level_anxiety_field.setText('5')
        self.dialog.date_edit.setDate(QtCore.QDate.currentDate())

        self.dialog.submit()

        mock_insert.assert_called_once()

    @patch.object(QMessageBox, 'warning')
    def test_submit_with_missing_fields(self, mock_warning):
        self.dialog.submit()
        mock_warning.assert_called_with(self.dialog, "Warning", "Please fill in all required fields.")

    @patch.object(QMessageBox, 'warning')
    def test_submit_with_invalid_email(self, mock_warning):
        self.dialog.first_name_field.setText('John')
        self.dialog.last_name_field.setText('Doe')
        self.dialog.email_field.setText('invalid-email')
        self.dialog.level_anxiety_field.setText('5')
        self.dialog.contact_number_field.setText('1234567890')
        self.dialog.id_number_field.setText('123456789')
        self.dialog.date_edit.setDate(QtCore.QDate.currentDate())
        self.dialog.submit()

        mock_warning.assert_called_with(self.dialog, "Warning", "Invalid email address.")


class TestExistingParticipantDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)

    def setUp(self):
        self.dialog = ExistingParticipantDialog(title="SEARCH PARTICIPANTS")
        self.dialog.show()  # Ensure the dialog is visible

    def test_initial_ui_state(self):
        self.assertEqual(self.dialog.windowTitle(), "SEARCH PARTICIPANTS")

    @patch('RMI_Simulator.Participants.database.find_participant',
           return_value={'first_name': 'Jane', 'last_name': 'Doe', 'age': 30, 'sex': 'Female', 'level_anxiety': '5',
                         'email': 'jane.doe@example.com', 'birthdate': '1994-08-15'})
    def test_submit_with_valid_id(self, mock_find):
        self.dialog.id_field.setText('123')
        self.dialog.submit()

        expected_text = "First Name: Jane\nLast Name: Doe\nAge: 30\nSex: Female"
        self.assertEqual(self.dialog.participant_info.text(), expected_text)
        mock_find.assert_called_once_with('123')

    @patch('RMI_Simulator.Participants.database.find_participant', return_value=None)
    def test_submit_with_invalid_id(self, mock_find):
        self.dialog.id_field.setText('999')
        self.dialog.submit()

        self.assertEqual(self.dialog.participant_info.text(), "participant not found")
        mock_find.assert_called_once_with('999')


if __name__ == '__main__':
    unittest.main()


class TestExistingParticipantDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)

    def setUp(self):
        self.dialog = ExistingParticipantDialog(title="SEARCH PARTICIPANTS")
        self.dialog.show()  # Ensure the dialog is shown for testing

    def test_initial_ui_state(self):
        self.assertEqual(self.dialog.windowTitle(), "SEARCH PARTICIPANTS")

    @patch('RMI_Simulator.Participants.database.find_participant',
           return_value={'first_name': 'Jane', 'last_name': 'Doe', 'age': 30, 'sex': 'Female', 'level_anxiety': '5',
                         'email': 'jane.doe@example.com', 'birthdate': '1994-08-15'})
    def test_submit_with_valid_id(self, mock_find):
        self.dialog.id_field.setText('123')
        self.dialog.submit()

        expected_text = "First Name: Jane\nLast Name: Doe\nAge: 30\nSex: Female"
        self.assertEqual(self.dialog.participant_info.text(), expected_text)
        mock_find.assert_called_once_with('123')

    @patch('RMI_Simulator.Participants.database.find_participant', return_value=None)
    def test_submit_with_invalid_id(self, mock_find):
        self.dialog.id_field.setText('999')
        self.dialog.submit()

        self.assertEqual(self.dialog.participant_info.text(), "participant not found")
        mock_find.assert_called_once_with('999')


if __name__ == '__main__':
    unittest.main()
