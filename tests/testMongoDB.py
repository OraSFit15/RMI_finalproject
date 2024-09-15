import unittest
from unittest.mock import MagicMock
from RMI_Simulator.database import MongoDB  # Assurez-vous que le nom du module est correct

class TestMongoDB(unittest.TestCase):
    def setUp(self):
        self.db_name = 'test_db'
        self.collection_names = ['test_collection']
        self.db = MongoDB(self.db_name, self.collection_names)
        # Mock the collections attribute directly
        self.db.collections = {
            'test_collection': MagicMock()
        }

    def tearDown(self):
        # Optionally: clean up resources
        pass

    def test_insert_one_success(self):
        # Configure the mock to succeed
        self.db.collections['test_collection'].insert_one.return_value = True
        result = self.db.insert_one('test_collection', {'name': 'Test'})
        self.assertTrue(result)
        # Verify the method call
        self.db.collections['test_collection'].insert_one.assert_called_once_with({'name': 'Test'})

    def test_find_one_success(self):
        # Configure the mock to return a result
        self.db.collections['test_collection'].find_one.return_value = {'name': 'Test'}
        result = self.db.find_one('test_collection', {'name': 'Test'})
        self.assertEqual(result['name'], 'Test')
        # Verify the method call
        self.db.collections['test_collection'].find_one.assert_called_once_with({'name': 'Test'})

    def test_find_one_failure(self):
        # Configure the mock to return None
        self.db.collections['test_collection'].find_one.return_value = None
        result = self.db.find_one('test_collection', {'name': 'Nonexistent'})
        self.assertIsNone(result)
        # Verify the method call
        self.db.collections['test_collection'].find_one.assert_called_once_with({'name': 'Nonexistent'})

if __name__ == '__main__':
    unittest.main()
