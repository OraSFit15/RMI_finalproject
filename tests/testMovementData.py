import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from RMI_Simulator.database import MovementData  # Import MovementData from the actual module name

class TestMovementData(unittest.TestCase):

    def setUp(self):
        # Create a mock MongoDB collection
        self.mock_collection = MagicMock()
        # Initialize MovementData with the mocked collection
        self.movement_data = MovementData(collection=self.mock_collection, db=None)

    def test_save_test_data(self):
        # Define the test data
        test_data = [1, 2, 3, 4, 5]
        participant = {'id': 'participant1', 'name': 'John Doe'}
        bodypart = 'arm'

        # Create a fixed datetime object for comparison
        fixed_datetime = datetime(2024, 8, 19, 11, 12, 48, 807613, tzinfo=timezone.utc)

        # Mock count_documents to return 0 for the new test
        self.mock_collection.count_documents.return_value = 0

        # Patch datetime to control utcnow()
        with patch('database.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = fixed_datetime

            # Call the method
            self.movement_data.save_test_data(test_data, participant, bodypart)

            # Verify that count_documents was called with the correct parameters
            self.mock_collection.count_documents.assert_called_once_with({'participant.id': participant['id']})

            # Create the expected document using the fixed datetime
            expected_doc = {
                "participant": participant,
                "test_id": 1,
                "test_data": test_data,
                "test_result": 'Unset',
                "mri_result": 'Unset',
                "timestamp": fixed_datetime,
                "bodypart": bodypart,
                "movement_amount": len(test_data),
                "note": 'Unset'
            }

            # Verify that insert_one was called with the correct document
            self.mock_collection.insert_one.assert_called_once_with(expected_doc)

    def test_get_participant_data(self):
        # Mock the find method to return a cursor-like object
        mock_cursor = MagicMock()
        self.mock_collection.find.return_value = mock_cursor

        # Call the method
        result = self.movement_data.get_participant_data('participant1')

        # Verify that find was called with the correct parameters
        self.mock_collection.find.assert_called_once_with({'participant.id': 'participant1'})

        # Verify that the result is the mocked cursor
        self.assertEqual(result, mock_cursor)

    def test_update_test_result(self):
        # Call the method
        self.movement_data.update_test_result('participant1', 1, 'Positive', 'Clear')

        # Verify that update_one was called with the correct parameters
        self.mock_collection.update_one.assert_called_once_with(
            {'participant_id': 'participant1', 'test_id': 1},
            {'$set': {'test_result': 'Positive', 'mri_result': 'Clear'}}
        )

    def test_update_note(self):
        # Call the method
        self.movement_data.update_note('participant1', 1, 'New note')

        # Verify that update_one was called with the correct parameters
        self.mock_collection.update_one.assert_called_once_with(
            {'participant_id': 'participant1', 'test_id': 1},
            {'$set': {'note': 'New note'}}
        )

if __name__ == '__main__':
    unittest.main()
