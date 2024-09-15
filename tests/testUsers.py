import unittest
from unittest.mock import MagicMock, patch
from io import StringIO
from RMI_Simulator.database import Users
import base64
import bcrypt # Assurez-vous que ce nom de module est correct

class TestUsers(unittest.TestCase):
    def setUp(self):
        # Mock de la base de données
        self.mock_db = MagicMock()
        self.mock_db.find.return_value = []  # Configure le mock pour la méthode find
        self.users = Users(self.mock_db)

    def test_check_user_success(self):
        # Hachage du mot de passe et encodage en base64 pour le mock
        password = 'password'
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        encoded_password = base64.b64encode(hashed_password).decode('utf-8')
        self.mock_db.find_one.return_value = {'username': 'testuser', 'password': encoded_password}

        result = self.users.check_user('testuser', password)
        self.assertTrue(result)

    def test_check_user_failure(self):
        # Hachage du mot de passe et encodage en base64 pour le mock
        password = 'password'
        wrong_password = 'wrongpassword'
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        encoded_password = base64.b64encode(hashed_password).decode('utf-8')
        self.mock_db.find_one.return_value = {'username': 'testuser', 'password': encoded_password}

        result = self.users.check_user('testuser', wrong_password)
        self.assertFalse(result)

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_users(self, mock_stdout):
        # Configurez le mock pour `find()`
        self.mock_db.collections['USERS'].find.return_value = [
            {'username': 'testuser', 'password': 'hashed_password'}
        ]
        # Exécutez la méthode à tester
        self.users.print_users()
        # Capturez la sortie
        output = mock_stdout.getvalue().strip()
        # Vérifiez la sortie
        expected_output = "{'username': 'testuser', 'password': 'hashed_password'}"
        print(f"Captured output: {output}")  # Debugging line
        self.assertIn(expected_output, output)

if __name__ == '__main__':
    unittest.main()
