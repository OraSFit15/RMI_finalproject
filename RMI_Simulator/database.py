import base64
import hashlib
import random
import string
from datetime import datetime, timezone

import bcrypt
import pymongo
from pymongo import MongoClient, errors
from pymongo.database import Database

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

    def __init__(self, collection, db: Database):
        """
        Initializes the MovementData object.

        Args:
            collection (pymongo.collection.Collection): The MongoDB collection object for movement data.
        """
        self.collection = collection
        self._db = db

    def save_test_data(self, test_data, participant, bodypart):
        """
        Saves the test data for a participant to the movement data collection.

        Args:
            test_data (list): The test data to save.
            participant (dict): The participant details.
            bodypart (str): The body part related to the test.

        Returns:
            None
        """
        print("Saving test data...")

        # Get the next test_id by counting existing documents for the participant
        next_test_id = self.collection.count_documents({'participant.id': participant['id']}) + 1
        movement_amount = len(test_data)
        participant_id = participant['id']  # Assuming 'participant' is a dictionary and 'id' is the participant's ID
        query = {'id': participant_id}
        participant_document = self._db['PARTICIPANTS'].find_one(query)

        # Initialize anxiety_level to a default value
        anxiety_level = 'Not Available'

        if participant_document:
            # Extract the anxiety level from the participant's document
            anxiety_level = participant_document.get('level_anxiety', 'Not Available')
            print(f"Anxiety Level: {anxiety_level}")
        else:
            print("Participant not found.")
        if movement_amount == 0:
            doc = {
                "participant": participant,
                "test_id": next_test_id,
                "test_data": test_data,
                "test_result": 'Passed',
                "mri_result": 'Passed',
                "timestamp": datetime.now(timezone.utc),
                "bodypart": bodypart,
                "movement_amount": movement_amount,
                "note": 'Unset',
                "anxiety_level": anxiety_level
            }
        else:
            doc = {
                "participant": participant,
                "test_id": next_test_id,
                "test_data": test_data,
                "test_result": 'Unset',
                "mri_result": 'Unset',
                "timestamp": datetime.now(timezone.utc),
                "bodypart": bodypart,
                "movement_amount": movement_amount,
                "note": 'Unset',
                "anxiety_level": anxiety_level
            }

        # Insert document into the collection
        result = self.collection.insert_one(doc)

        if result.acknowledged:
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
        return self.collection.find({'participant.id': participant_id})

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


def id_exists(db, id_number):
    """
    Checks if a participant with the given ID number already exists.

    Args:
        db (MongoDB): The MongoDB object for database operations.
        id_number (str): The ID number to check.

    Returns:
        bool: True if a participant with the ID number exists, False otherwise.
    """
    # Vérifiez si id_number est une chaîne de caractères (str) avant d'appeler encode()
    if not isinstance(id_number, str):
        return False

    # Utilisez une chaîne de caractères encodée pour obtenir le hachage SHA-256

    participants_collection = db.collections['PARTICIPANTS']
    hashed_id = hashlib.sha256(id_number.encode()).hexdigest()
    return participants_collection.find_one({'id': hashed_id}) is not None


def email_exists(db, email):
    """
    Checks if a participant with the given email already exists.

    Args:
        db (MongoDB): The MongoDB object for database operations.
        email (str): The email to check.

    Returns:
        bool: True if a participant with the email exists, False otherwise.
    """
    # Vérifiez si email est une chaîne de caractères (str)
    if not isinstance(email, str):
        return False

    participants_collection = db.collections['PARTICIPANTS']
    print("okk")
    # Recherchez l'email dans toute la base de données, pas seulement dans la collection des participants
    return participants_collection.find_one({'email': email}) is not None


from pymongo.errors import PyMongoError


def insert_participant(first_name, last_name, sex, id_number, birthdate, age, email, contact, level_anxiety):
    client = get_client()
    db = client['MRI_PROJECT']
    participants_collection = db['PARTICIPANTS']

    try:
        if id_exists(db, id_number):
            print("Participant with this ID number already exists.")
            client.close()
            return False

        if email_exists(db, email):
            print("Participant with this email already exists.")
            client.close()
            return False

        participant_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        hashed_id = hashlib.sha256(id_number.encode()).hexdigest()

        participants_collection.insert_one({
            'id_generate': participant_id,
            'first_name': first_name,
            'last_name': last_name,
            'sex': sex,
            'id': hashed_id,
            'birthdate': birthdate,
            'age': age,
            'email': email,
            'contact': contact,
            'level_anxiety': level_anxiety,
        })
        client.close()
        return participant_id
    except PyMongoError as e:
        print(f"Error inserting participant: {e}")
        client.close()
        return False


def set_level(id_number, new_level):
    """
    Updates the anxiety level of a participant in the MongoDB collection.

    Args:
        id_number (str): The ID number of the participant.
        new_level (str): The new anxiety level to set.

    Returns:
        bool: True if update was successful, False otherwise.
    """
    client = MongoClient('mongodb://localhost:27017/')  # Update with your MongoDB connection string
    db = client['MRI_PROJECT']
    participants_collection = db['PARTICIPANTS']

    try:
        # Hash the id_number to match the stored hashed_id
        hashed_id = hashlib.sha256(id_number.strip().encode()).hexdigest()
        print(id_number)
        print(hashed_id)
        # Check if the participant exists
        participant = participants_collection.find_one({'id': hashed_id})
        if not participant:
            print("Participant with this ID number does not exist.")
            client.close()
            return False

        # Update the anxiety level
        result = participants_collection.update_one(
            {'id': hashed_id},
            {'$set': {'level_anxiety': new_level}}
        )

        if result.modified_count > 0:
            print(f"Anxiety level updated successfully for participant {id_number}.")
            client.close()
            return True
        else:
            print("No changes made. Anxiety level might be the same as the existing value.")
            client.close()
            return False

    except errors.PyMongoError as e:
        print(f"Error updating anxiety level: {e}")
        client.close()
        return False


def find_participant(id_number):
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
        # Hashing participant_id with SHA-256
        hashed_id = hashlib.sha256(id_number.encode()).hexdigest()

        participant = participants_collection.find_one({'id': hashed_id})
        client.close()
        return participant
    except PyMongoError:
        client.close()
        return None
