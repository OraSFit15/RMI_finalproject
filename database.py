import random
import string
from datetime import datetime
import pymongo
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import bcrypt
import base64

"""change participant from patient name"""
class MongoDB:
    """
    A MongoDB database wrapper.

    Attributes:
        client (pymongo.MongoClient): The MongoDB client object.
        db (pymongo.database.Database): The MongoDB database object.
        collections (dict): A dictionary mapping collection names to their corresponding collection objects.

    Methods:
        insert_one: Inserts a document into the specified collection.
        find_one: Finds and returns a single document from the specified collection.
    """

    def __init__(self, database_name, collection_names):
        """
        Initializes the MongoDB object.

        Args:
            database_name (str): The name of the MongoDB database.
            collection_names (list): A list of collection names.
        """
        self.client = MongoClient('localhost', 27017)
        self.db = self.client[database_name]
        self.collections = {name: self.db[name] for name in collection_names}

    def insert_one(self, collection_name, data):
        """
        Inserts a document into the specified collection.

        Args:
            collection_name (str): The name of the collection to insert the document into.
            data (dict): The document data to insert.

        Returns:
            bool: True if the insertion is successful, False otherwise.
        """
        try:
            self.collections[collection_name].insert_one(data)
            return True
        except PyMongoError as e:
            print(f"Error inserting data into {collection_name}: {e}")
            return False

    def find_one(self, collection_name, filter_dict):
        """
        Finds and returns a single document from the specified collection.

        Args:
            collection_name (str): The name of the collection to search.
            filter_dict (dict): The filter criteria to find the document.

        Returns:
            dict: The found document or None if not found.
        """
        return self.collections[collection_name].find_one(filter_dict)


class Users:
    """
    User management class for interacting with the 'USERS' collection in the database.

    Attributes:
        db (MongoDB): The MongoDB object for database operations.

    Methods:
        create_user: Creates a new user with the specified username and password.
        check_user: Checks if the provided username and password match a user in the database.
        check_username: Checks if a username already exists in the database.
        print_users: Prints all users in the 'USERS' collection.
    """

    def __init__(self, db):
        """
        Initializes the Users object.

        Args:
            db (MongoDB): The MongoDB object for database operations.
        """
        self.db = db

    def create_user(self, username, password):
        """
        Creates a new user with the specified username and password.

        Args:
            username (str): The username for the new user.
            password (str): The password for the new user.

        Returns:
            bool: True if the user creation is successful, False otherwise.
        """
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        hashed_password_str = base64.b64encode(hashed_password).decode('utf-8')
        result = self.db.insert_one('USERS', {'username': username, 'password': hashed_password_str})

        if result:
            print(f"User {username} created successfully.")
        else:
            print(f"Failed to create user {username}.")

        return result

    def check_user(self, username, password, collection=None):
        """ """
        if collection is not None:
            user = self.db.find_one(collection, {'username': username})
        else:
            user = self.db.find_one({'username': username})
        if not user:
            return False
        hashed_password = base64.b64decode(user['password'].encode('utf-8'))
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

    def check_username(self, username):
        """
        Checks if a username already exists in the database.

        Args:
            username (str): The username to check.

        Returns:
            bool: True if the username exists, False otherwise.
        """
        return self.db.find_one('USERS', {'username': username}) is not None

    def print_users(self):
        """
        Prints all users in the 'USERS' collection.
        """
        users = self.db.collections['USERS'].find()
        for user in users:
            print(user)


class Participants:
    """
    participant management class for interacting with the 'participantS' collection in the database.

    Attributes:
        db (MongoDB): The MongoDB object for database operations.

    Methods:
        add_participant: Adds a new participant with the specified details to the 'participantS' collection.
    """

    def __init__(self, db):
        """
        Initializes the participants object.

        Args:
            db (MongoDB): The MongoDB object for database operations.
        """
        self.db = db

    def add_participant(self, first_name, last_name, age, sex):
        """
        Adds a new participant with the specified details to the 'participantS' collection.

        Args:
            first_name (str): The first name of the participant.
            last_name (str): The last name of the participant.
            age (int): The age of the participant.
            sex (str): The sex of the participant.

        Returns:
            bool: True if the participant addition is successful, False otherwise.
        """
        return self.db.insert_one('participantS',
                                  {'first_name': first_name, 'last_name': last_name, 'age': age, 'sex': sex})


class MovementData:
    """
    Movement data management class for interacting with the movement data collection in the database.

    Attributes:
        collection (pymongo.collection.Collection): The MongoDB collection object for movement data.

    Methods:
        save_test_data: Saves the test data for a participant to the movement data collection.
        get_participant_data: Retrieves the movement data for a participant from the movement data collection.
        update_test_result: Updates the test result and MRI result for a specific test of a participant.
        update_note: Updates the note for a specific test of a participant.
    """

    def __init__(self, collection):
        """
        Initializes the MovementData object.

        Args:
            collection (pymongo.collection.Collection): The MongoDB collection object for movement data.
        """
        self.collection = collection

    def save_test_data(self, test_data, participant_id):
        """
        Saves the test data for a participant to the movement data collection.

        Args:
            test_data (list): The test data to save.
            participant_id (str): The ID of the participant.

        Returns:
            None
        """
        print("Saving test data...")

        # Get the next test_id by counting existing documents for the participant
        next_test_id = self.collection.count_documents({'participant_id': participant_id}) + 1

        doc = {
            "participant_id": participant_id,
            "test_id": next_test_id,
            "test_data": test_data,
            "test_result": 'Unset',
            "mri_result": 'Unset',
            "timestamp": datetime.utcnow(),
            "movement_amount": len(test_data),
            "note": 'Unset'
        }

        if self.collection.insert_one(doc):
            print("Test data saved successfully.")
        else:
            print("Error saving test data.")

    def get_participant_data(self, participant_id):
        """
        Retrieves the movement data for a participant from the movement data collection.

        Args:
            participant_id (str): The ID of the participant.

        Returns:
            pymongo.cursor.Cursor: The cursor object containing the retrieved movement data.
        """
        return self.collection.find({'participant_id': participant_id})

    def update_test_result(self, participant_id, test_id, test_result, mri_result):
        """
        Updates the test result and MRI result for a specific test of a participant.

        Args:
            participant_id (str): The ID of the participant.
            test_id (int): The ID of the test.
            test_result (str): The test result to update.
            mri_result (str): The MRI result to update.

        Returns:
            None
        """
        self.collection.update_one({'participant_id': participant_id, 'test_id': test_id},
                                   {'$set': {'test_result': test_result, 'mri_result': mri_result}})

    def update_note(self, participant_id, test_id, new_note):
        """
        Updates the note for a specific test of a participant.

        Args:
            participant_id (str): The ID of the participant.
            test_id (int): The ID of the test.
            new_note (str): The new note to update.

        Returns:
            None
        """
        self.collection.update_one({'participant_id': participant_id, 'test_id': test_id},
                                   {'$set': {'note': new_note}})


def get_client():
    """
    Retrieves and returns a MongoDB client object.

    Returns:
        pymongo.MongoClient: The MongoDB client object.
    """
    connection_string = "mongodb://localhost:27017"
    return MongoClient(connection_string)


def insert_participant(first_name, last_name, age, sex):
    """
    Inserts a new participant into the 'participants' collection in the database.

    Args:
        first_name (str): The first name of the participant.
        last_name (str): The last name of the participant.
        age (int): The age of the participant.
        sex (str): The sex of the participant.

    Returns:
        str or bool: The generated participant ID if successful, False otherwise.
    """
    client = get_client()
    db = client['MRI_PROJECT']
    participants_collection = db['PARTICIPANTS']
    participant_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    try:
        participants_collection.insert_one({
            'id': participant_id,
            'first_name': first_name,
            'last_name': last_name,
            'age': age,
            'sex': sex
        })
        client.close()
        return participant_id
    except PyMongoError:
        client.close()
        return False


def find_participant(participant_id):
    """
    Finds and returns a participant from the 'participants' collection in the database.

    Args:
        participant_id (str): The ID of the participant to find.

    Returns:
        dict or None: The found participant document or None if not found.
    """
    client = get_client()
    db = client['MRI_PROJECT']
    participants_collection = db['PARTICIPANTS']

    try:
        participant = participants_collection.find_one({'id': participant_id})
        client.close()
        return participant
    except PyMongoError:
        client.close()
        return None


def main():
    db = MongoDB('MRI_PROJECT', ['USERS', 'PARTICIPANTS', 'MOVEMENT_DATA'])
    users = Users(db)
    participants = Participants(db)
    movement_data = MovementData(db)
    create_user = users.create_user("admin", "admin")  # IN CASE OF NEW DATABASE
    users.print_users()
    if users.check_user('admin', 'admin', 'USERS'):
        print("User found.")
    else:
        print("No user found with username: admin")


if __name__ == '__main__':

    main()
