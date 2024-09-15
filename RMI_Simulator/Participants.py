import datetime

import pygame
from PyQt5.QtCore import *
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import *
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QPushButton, QMessageBox, QTableWidgetItem
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from RMI_Simulator import database
from RMI_Simulator.GUI import TitleBar
from RMI_Simulator.Menu import FramelessWindow
from RMI_Simulator.Menu import MenuWindow
from RMI_Simulator.database import MongoDB

db = MongoDB('MRI_PROJECT', ['USERS', 'PARTICIPANTS', 'movement_data'])
from PyQt5.QtWidgets import QVBoxLayout, QWidget


class NewParticipantDialog(QDialog):
    """A dialog for entering information about a new participant."""
    participant_id_generated = pyqtSignal(str)

    def __init__(self, parent=None, title="NEW PARTICIPANT FORM"):
        super().__init__(parent)
        self.mousePress = None
        self.moveWindow = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(450, 100, 550, 200)
        self.setWindowTitle(title)

        # Initialize main layout
        self.main_layout = QVBoxLayout()

        # Add title bar to main layout
        self.title_bar = TitleBar(self, title)
        self.main_layout.addWidget(self.title_bar)

        self.label_email = QLabel("Email:")
        self.email_field = QLineEdit()
        email_validator = QRegularExpressionValidator(QRegularExpression(r'^[\w\.-]+@[\w\.-]+\.\w+$'))
        self.email_field.setValidator(email_validator)
        self.label_level_anxiety = QLabel("Level of Anxiety:")
        self.level_anxiety_field = QLineEdit()
        validator_level = QIntValidator(0, 90)
        self.level_anxiety_field.setValidator(validator_level)
        self.contact_number_label = QLabel("Contact Number")
        self.contact_number_field = QLineEdit()
        validator_nb = QIntValidator(0, 999999999)
        self.contact_number_field.setValidator(validator_nb)
        self.submit_button_side = QPushButton("ADDITIONAL INFORMATION")
        self.submit_button_side.setCursor(Qt.PointingHandCursor)
        self.first_name_field = QLineEdit()
        self.last_name_field = QLineEdit()
        self.id_number_label = QLabel("Id Number:")
        self.id_number_field = QLineEdit()
        validator_id = QIntValidator(0, 999999999)
        self.id_number_field.setValidator(validator_id)
        self.sex_field = QComboBox()
        self.sex_field.addItems(['Male', 'Female', 'Other'])
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.age_label = QLabel()
        self.selected_date_label = QLabel()
        self.submit_button = QPushButton("SAVE")
        self.submit_button.clicked.connect(self.submit)
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.title_bar)

        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)

        self.columns_layout = QHBoxLayout()

        self.right_layout = QVBoxLayout()
        self.right_layout.addWidget(self.label_email)
        self.right_layout.addWidget(self.email_field)
        self.right_layout.addWidget(self.label_level_anxiety)
        self.right_layout.addWidget(self.level_anxiety_field)
        self.right_layout.addWidget(self.contact_number_label)
        self.right_layout.addWidget(self.contact_number_field)
        self.right_layout.addWidget(self.submit_button_side)
        self.right_layout.addWidget(self.submit_button)
        self.right_layout.addStretch()

        self.left_layout = QVBoxLayout()
        self.left_layout.addWidget(QLabel("First Name:"))
        self.left_layout.addWidget(self.first_name_field)
        self.left_layout.addWidget(QLabel("Last Name:"))
        self.left_layout.addWidget(self.last_name_field)
        self.left_layout.addWidget(QLabel("Gender:"))
        self.left_layout.addWidget(self.sex_field)
        self.left_layout.addWidget(self.id_number_label)
        self.left_layout.addWidget(self.id_number_field)
        self.left_layout.addWidget(QLabel("Date of Birth:"))
        self.left_layout.addWidget(self.date_edit)
        self.left_layout.addWidget(self.selected_date_label)

        # Add columns to main layout
        self.columns_layout.addLayout(self.left_layout)
        self.columns_layout.addLayout(self.right_layout)

        # Add columns layout to main layout
        self.main_layout.addLayout(self.columns_layout)
        self.submit_button_side.clicked.connect(self.handle_additional_information_button_clicked)

        # Connect dateChanged signal
        # Apply styles
        self.setStyleSheet("""
            QDialog {
                background-color: #f8cba8;
            }
            QLabel {
                color: black;
                font-weight: bold;
                background-color: #f8cba8;
            }
            QLineEdit, QComboBox, QDateEdit {
                background-color: #fbe5d6;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 3px;
            }
            QPushButton {
                background-color: #f4b283;
                color: black;
                font-weight: bold;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:pressed {
                background-color: #8c3e13;
            }
        """)

    def submit(self):
        # Vérifiez si tous les champs requis sont remplis
        if self.first_name_field.text() == '' or self.last_name_field.text() == '':
            QMessageBox.warning(self, "Warning", "Please fill in all required fields.")
            return

        # Obtenez la date de naissance sélectionnée et calculez l'âge
        selected_date = self.date_edit.date().toPyDate()
        selected_date_str = selected_date.strftime("%Y-%m-%d")
        self.selected_date_label.setText(selected_date_str)
        selected_date = datetime.datetime(selected_date.year, selected_date.month, selected_date.day)
        current_date = datetime.datetime.now()
        age = current_date.year - selected_date.year - (
                (current_date.month, current_date.day) < (selected_date.month, selected_date.day))

        if age < 0:
            QMessageBox.warning(self, "Warning", "Invalid date of birth.")
            return

        id_number = self.id_number_field.text()
        if not id_number.isdigit() or len(id_number) != 9:
            QMessageBox.warning(self, "Warning", "Invalid ID number. Please enter a 9-digit number.")
            return

        level = self.level_anxiety_field.text()
        if not level.isdigit() or len(level) not in (1, 2):
            QMessageBox.warning(self, "Warning", "Level number please enter a number from 0 to 10")
            return

        phone_number = self.contact_number_field.text()
        if not phone_number.isdigit() or len(phone_number) != 10:
            QMessageBox.warning(self, "Warning", "Invalid phone number. Please enter a 10-digit number.")
            return

        if not self.email_field.hasAcceptableInput():
            QMessageBox.warning(self, "Warning", "Invalid email address.")
            return

        # Si toutes les validations sont réussies, insérez les données dans la base de données
        success = database.insert_participant(
            self.first_name_field.text(),
            self.last_name_field.text(),
            self.sex_field.currentText(),
            id_number,
            selected_date_str,
            age,
            self.email_field.text(),
            phone_number,
            self.level_anxiety_field.text(),
        )

        if success:
            self.participant_id_generated.emit(str(success))
            self.close()
        else:
            QMessageBox.critical(self, "Error", "DB ERROR")

    def show_selected_date(self, age):
        selected_date = self.date_edit.date().toString(Qt.ISODate)
        self.selected_date_label.setText(selected_date)

    def mousePressEvent(self, event):
        """Event handler for mouse press events."""
        self.mousePress = event.pos()

    def mouseMoveEvent(self, event):
        """Event handler for mouse move events."""
        if self.mousePress is None:
            return
        self.moveWindow = event.globalPos() - self.mousePress
        self.move(self.moveWindow)

    def mouseReleaseEvent(self, event):
        """Event handler for mouse release events."""
        self.mousePress = None
        self.moveWindow = None

    def closeEvent(self, event):
        menuWindow = MenuWindow()
        menuWindow.show()

    def handle_additional_information_button_clicked(self):
        """Handles the click event of the additional information button."""
        button_clicked = self.sender()
        if button_clicked == self.submit_button_side:
            note_dialog = NoteDialog(note="")
            note_dialog.exec_()


class ExistingParticipantDialog(QDialog):
    """A dialog for selecting an existing participant."""
    """Initializes the ExistingparticipantDialog class.

        Args:
            parent (QWidget): The parent widget.
            title (str): The title of the dialog.
        """
    participant_id_generated = pyqtSignal(str)

    def __init__(self, parent=None, title="SEARCH PARTICIPANTS"):
        super().__init__(parent)
        self.moveWindow = None
        self.mousePress = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle(title)
        self.setGeometry(450, 100, 550, 200)
        # Initialize title bar first
        self.title_bar = TitleBar(self, title)

        # Initialize main layout
        self.main_layout = QVBoxLayout()

        # Add title bar to main layout
        self.main_layout.addWidget(self.title_bar)

        # Add title separator
        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)

        self.id_number_label = QLabel("ID NUMBER :")
        self.id_field = QLineEdit()

        # Connect to database
        self.client = database.get_client()
        self.db = self.client['MRI_PROJECT']
        self.participants_collection = self.db['participants']

        self.main_layout.addWidget(self.id_number_label)
        self.main_layout.addWidget(self.id_field)
        self.submit_button = QPushButton("INITIATE SEARCH")
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.clicked.connect(self.submit)
        self.main_layout.addWidget(self.submit_button)

        self.participant_info = QLabel()
        self.main_layout.addWidget(self.participant_info)

        # Set main layout for the dialog
        self.setLayout(self.main_layout)
        self.participant_details_window = ParticipantDetailsWindow({})

        # Apply styles
        self.setStyleSheet("""
               QDialog {
                   background-color: #f8cba8;
               }
               QLabel {
                   color: black;
                   font-weight: bold;
                   background-color: #f8cba8;
               }
               QLineEdit, QComboBox, QDateEdit {
                   background-color: #fbe5d6;
                   border: 1px solid #c55b26;
                   border-radius: 5px;
                   padding: 3px;
               }
               QPushButton {
                   background-color: #f4b283;
                   color: black;
                   font-weight: bold;
                   border: 1px solid #c55b26;
                   border-radius: 5px;
                   padding: 6px;
               }
               QPushButton:pressed {
                   background-color: #8c3e13;
               }
           """)

    def submit(self):
        """Submits the selected participant ID and emits the generated participant ID signal."""
        participant = database.find_participant(self.id_field.text())
        participant_id = self.id_field.text()

        if participant:
            self.participant_info.setText(
                f"First Name: {participant['first_name']}\nLast Name: {participant['last_name']}\nAge: {participant['age']}\nSex: {participant['sex']}")
            self.participant_id_generated.emit(self.id_field.text())
            self.participant_details_window = ParticipantDetailsWindow(participant)
            self.participant_details_window.show_details(participant, participant_id)
            self.participant_details_window.show()
            self.close()

        else:
            self.participant_info.setText("participant not found")

    def mousePressEvent(self, event):
        """Event handler for mouse press events."""
        self.mousePress = event.pos()

    def mouseMoveEvent(self, event):
        """Event handler for mouse move events."""
        if self.mousePress is None:
            return
        self.moveWindow = event.globalPos() - self.mousePress
        self.move(self.moveWindow)

    def mouseReleaseEvent(self, event):
        """Event handler for mouse release events."""
        self.mousePress = None
        self.moveWindow = None

    def closeEvent(self, event):
        menuWindow = MenuWindow()
        menuWindow.show()


class ParticipantDetailsWindow(QDialog):
    """A window for handling participant details."""

    participant_id_received = pyqtSignal(str)

    def __init__(self, participant, parent=None, title="PARTICIPANT PROFILE"):
        super().__init__(parent)

        self.table = QTableWidget()
        self.moveWindow = None
        self.mousePress = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(450, 100, 700, 500)

        self.participant = participant

        # Initialize the main layout
        self.main_layout = QVBoxLayout()
        self.left_group_box = QGroupBox()
        self.left_group_box.setFixedSize(400, 500)

        self.right_group_box = QGroupBox()
        self.right_group_box.setFixedSize(400, 500)

        # Create a title bar
        self.title_bar = TitleBar(self, title)
        self.main_layout.addWidget(self.title_bar)

        # Add a separator
        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)
        label_styles_1 = """
            QLabel {
                background-color: #fbe5d6;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 3px;
            }
        """

        # Create layouts for left and right columns
        self.columns_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()

        # Widgets for the left column
        self.left_layout.addWidget(QLabel("ID NUMBER :"))
        self.id_field = QLabel()
        self.id_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.id_field)

        self.left_layout.addWidget(QLabel("First Name:"))
        self.first_name_field = QLabel()
        self.first_name_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.first_name_field)

        self.left_layout.addWidget(QLabel("Last Name:"))
        self.last_name_field = QLabel()
        self.last_name_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.last_name_field)

        self.left_layout.addWidget(QLabel("Birthdate:"))
        self.birthdate_field = QLabel()
        self.birthdate_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.birthdate_field)

        self.left_layout.addWidget(QLabel("Age:"))
        self.age_field = QLabel()
        self.age_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.age_field)

        self.left_layout.addWidget(QLabel("Gender:"))
        self.gender_field = QLabel()
        self.gender_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.gender_field)

        self.left_layout.addWidget(QLabel("Email:"))
        self.email_field = QLabel()
        self.email_field.setStyleSheet(label_styles_1)
        self.left_layout.addWidget(self.email_field)

        # Widgets for the right column
        self.right_layout.addWidget(QLabel("Level of Anxiety:"))

        # QLineEdit for editable anxiety level
        self.level_anxiety_field = QLineEdit()
        self.level_anxiety_field.setStyleSheet(label_styles_1)
        self.right_layout.addWidget(self.level_anxiety_field)

        # Button to modify anxiety level
        self.modify_button = QPushButton("Modify")
        self.modify_button.clicked.connect(self.modify_anxiety_level)
        self.right_layout.addWidget(self.modify_button)

        # Créer un layout horizontal pour la ligne des boutons
        self.button_layout_1 = QHBoxLayout()
        self.button_layout_2 = QHBoxLayout()

        self.hist_mri = QPushButton("HISTORY\nOF\nMRI TEST")
        self.hist_mri.setCursor(Qt.PointingHandCursor)
        self.hist_mri.clicked.connect(self._show_tests_history)
        self.button_layout_1.addWidget(self.hist_mri)

        self.hist_graph = QPushButton("HISTORY GRAPH\nOF\nMRI TEST")
        self.hist_graph.setCursor(Qt.PointingHandCursor)
        self.hist_graph.clicked.connect(self._show_tests_history_graph)
        self.button_layout_1.addWidget(self.hist_graph)
        self.hist_graph.setFixedSize(150, 65)

        self.right_layout.addLayout(self.button_layout_1)

        self.test = QPushButton("BEGIN TEST")
        self.test.setCursor(Qt.PointingHandCursor)
        self.button_layout_2.addWidget(self.test)
        self.test.clicked.connect(self.begin_test)
        self.test.setFixedSize(150, 65)

        self.right_layout.addLayout(self.button_layout_2)
        self.right_layout.addStretch()

        self.left_group_box.setLayout(self.left_layout)
        self.right_group_box.setLayout(self.right_layout)

        columns_layout = QHBoxLayout()
        columns_layout.addWidget(self.left_group_box)
        columns_layout.addWidget(self.right_group_box)

        # Add left and right layouts to the columns layout
        self.columns_layout.addWidget(self.left_group_box)
        self.columns_layout.addWidget(self.right_group_box)
        # Add the columns layout to the main layout
        self.main_layout.addLayout(self.columns_layout)

        # Set the main layout for the dialog
        self.setLayout(self.main_layout)

        self.setStyleSheet("""
                QDialog {
                    background-color: #f8cba8;
                }
                QLabel {
                color: black;
                font-weight: bold;
                background-color: #f8cba8;
            }
                QLineEdit, QComboBox, QDateEdit {
                    background-color: #fbe5d6;
                    border: 1px solid #c55b26;
                    border-radius: 5px;
                    padding: 3px;
                }
                QPushButton {
                    background-color: #f4b283;
                    color: black;
                    font-weight: bold;
                    border: 1px solid #c55b26;
                    border-radius: 5px;
                    padding: 6px;
                }
                QPushButton:pressed {
                    background-color: #8c3e13;
                }
            """)

    def modify_anxiety_level(self):
        # Logic to handle modifying the anxiety level
        # For example, you might want to open a dialog or update the database
        new_level = self.level_anxiety_field.text()
        print(f"New Anxiety Level: {new_level}")
        print(self.id_field)
        database.set_level(self.id_field.text(), new_level)

    def _show_tests_history_graph(self):
        tests = db.collections['movement_data']

        # Check if 'id' exists in self.participant
        if 'id' in self.participant:
            movement_data = list(tests.find({'participant.id': self.participant['id']}))

            # If movement_data is empty, return early
            if not movement_data:
                print("No movement data found.")
                return

            test_id_movements_map = {}
            for data in movement_data:
                test_id = data.get('test_id')
                movement_amount = data.get('movement_amount')
                if isinstance(test_id, (int, str)) and isinstance(movement_amount, (int, float)):
                    test_id_movements_map[test_id] = movement_amount

            # Sort movements by test_id
            sorted_movements_by_test_id = dict(sorted(test_id_movements_map.items()))

            tests_numbers = list(sorted_movements_by_test_id.keys())
            movements_amounts = list(sorted_movements_by_test_id.values())

            # Create a QDialog for displaying the plot
            plot_dialog = QDialog(self)
            plot_dialog.setWindowTitle('Test History Graph')
            plot_dialog.setGeometry(100, 100, 800, 600)

            # Set up the layout and plot
            plot_layout = QVBoxLayout()

            # Create matplotlib figure and canvas
            figure = Figure()
            canvas = FigureCanvas(figure)
            ax = figure.add_subplot(111)
            ax.plot(tests_numbers, movements_amounts, marker='o', linestyle='-', color='skyblue', markerfacecolor='red')
            ax.set_xlabel('Test Number')
            ax.set_ylabel('Amount of Movements per Test')
            ax.set_title(
                f'Movements Amount per Test - {self.participant["first_name"]} {self.participant["last_name"]}')
            ax.set_xticks(tests_numbers)
            ax.set_xticklabels(tests_numbers, rotation=45, ha='right')
            ax.autoscale()

            # Add canvas to the layout
            plot_layout.addWidget(canvas)
            plot_dialog.setLayout(plot_layout)

            # Show the plot dialog in a non-blocking way
            plot_dialog.show()

        else:
            print("ID not found in participant.")

    def show_details(self, participant_details, participant_id):
        """Affiche les détails du participant dans la fenêtre."""
        self.first_name_field.setText(f" {participant_details['first_name']}")
        self.last_name_field.setText(f" {participant_details['last_name']}")
        self.age_field.setText(f" {participant_details['age']}")
        self.id_field.setText(f" {participant_id}")
        self.level_anxiety_field.setText(f" {participant_details['level_anxiety']}")
        self.email_field.setText(f" {participant_details['email']}")
        self.birthdate_field.setText(f" {participant_details['birthdate']}")
        self.gender_field.setText(f" {participant_details['sex']}")

    def _show_tests_history(self):
        # Assuming you have a method to fetch movement data from the database
        tests = db.collections['movement_data']
        movement_data_cursor = tests.find({'participant.id': self.participant['id']})

        movement_data = []
        for data in movement_data_cursor:
            movement_data.append({
                'test_id': data.get('test_id'),
                'movement_amount': data.get('movement_amount'),
                'timestamp': data.get('timestamp'),
                'test_result': data.get('test_result', 'N/A'),
                'anxiety_level': data.get('anxiety_level', 'N/A'),

            })

        if movement_data:
            # Create the TestHistoryWindow instance and show it
            test_history_window = TestHistoryWindow(movement_data, self.participant)
            test_history_window.show()  # Or test_history_window.show() if you want a non-modal window
        else:
            print("No movement data available for the given participant ID.")

    def handle_participant_id(self, participant_id):
        """Handles the participant ID received from the caller.

                Args:
                    participant_id (str): The ID of the selected participant.
                """
        participant = database.find_participant(participant_id)
        if participant:
            participant_details_window = ParticipantDetailsWindow(participant)
            participant_details_window.show_details(participant, participant_id)  # Passer participant_id
            participant_details_window.show()
        else:
            # Handle the case when the participant is not found
            print(f"Participant with ID {participant_id} not found.")

    def mousePressEvent(self, event):
        """Event handler for mouse press events."""
        self.mousePress = event.pos()

    def mouseMoveEvent(self, event):
        """Event handler for mouse move events."""
        if self.mousePress is None:
            return
        self.moveWindow = event.globalPos() - self.mousePress
        self.move(self.moveWindow)

    def mouseReleaseEvent(self, event):
        """Event handler for mouse release events."""
        self.mousePress = None
        self.moveWindow = None

    def closeEvent(self, event):
        menuWindow = MenuWindow()
        menuWindow.show()

    def handle_additional_information_button_clicked(self):
        """Handles the click event of the additional information button."""
        button_clicked = self.sender()
        if button_clicked == self.submit_button_side:
            note_dialog = NoteDialog(note="")
            note_dialog.exec_()

    def begin_test(self):
        """Starts the test """
        begin_test = MainWindow(self.participant)
        begin_test.show()


class NoteDialog(QDialog):
    """A dialog for displaying and editing a note."""

    def __init__(self, note="", parent=None, title="ADDITIONAL INFORMATION"):
        """Initializes the NoteDialog class.

        Args:
            parent (QWidget): The parent widget.
            title (str): The title of the dialog.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(450, 100, 550, 200)

        # Initialize main layout
        self.main_layout = QVBoxLayout()

        # Add title bar to main layout
        self.title_bar = TitleBar(self, title)
        self.main_layout.addWidget(self.title_bar)

        # Add QTextEdit for note input
        self.note_text_edit = QTextEdit()
        self.note_text_edit.setMinimumSize(300, 200)
        self.main_layout.addWidget(self.note_text_edit)

        # Add OK button to save note
        self.ok_button = QPushButton("OK")
        self.ok_button.setCursor(Qt.PointingHandCursor)

        self.ok_button.clicked.connect(self.get_note)

        self.main_layout.addWidget(self.ok_button)

        # Set the main layout for the dialog
        self.setLayout(self.main_layout)

        self.setModal(True)  # Set the dialog as modal

        self.setStyleSheet("""
                QDialog {
                    background-color: #f8cba8;
                }
                QLabel {
                    color: black;
                    font-weight: bold;
                    background-color: #f8cba8;
                }
                QLineEdit, QComboBox, QDateEdit {
                    background-color: #fbe5d6;
                    border: 1px solid #c55b26;
                    border-radius: 5px;
                    padding: 3px;
                }
                QPushButton {
                    background-color: #f4b283;
                    color: black;
                    font-weight: bold;
                    border: 1px solid #c55b26;
                    border-radius: 5px;
                    padding: 6px;
                }
                QPushButton:pressed {
                    background-color: #8c3e13;
                }
            """)

    def get_note(self):
        """Returns the text of the note.

        Returns:
            str: The text of the note.
        """
        return self.note_text_edit.toPlainText()

    def mousePressEvent(self, event):
        """Event handler for mouse press events."""
        self.mousePress = event.pos()

    def mouseMoveEvent(self, event):
        """Event handler for mouse move events."""
        if self.mousePress is None:
            return
        self.moveWindow = event.globalPos() - self.mousePress
        self.move(self.moveWindow)

    def mouseReleaseEvent(self, event):
        """Event handler for mouse release events."""
        self.mousePress = None
        self.moveWindow = None


class TestHistoryWindow(QDialog):
    """A dialog for displaying the test history of a participant."""

    def __init__(self, movement_data, participant_id, parent=None, title="HISTORY WINDOW"):
        super().__init__(parent)
        self.movement_data = movement_data
        self.participant_id = participant_id
        self.init_ui()

    def init_ui(self):
        """Initializes the user interface of the dialog."""
        self.main_layout = QVBoxLayout(self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.title_bar = TitleBar(self, "TEST HISTORY")
        self.main_layout.addWidget(self.title_bar)

        # Add title separator
        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)

        # Create and configure the table widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['NUMBER', 'DATE', 'MOVEMENT AMOUNT', 'TEST RESULT', 'ANXIETY LEVEL'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.main_layout.addWidget(self.table)

        # Populate the table with test data
        self.populate_table(self.movement_data)

        self.setGeometry(450, 100, 800, 600)  # Adjust size as needed
        self.setStyleSheet("""
                  QDialog {
                      background-color: #f8cba8;
                  }
                  QLabel {
                      color: black;
                      font-weight: bold;
                      background-color: #f8cba8;
                  }
                  QLineEdit, QComboBox, QDateEdit {
                      background-color: #fbe5d6;
                      border: 1px solid #c55b26;
                      border-radius: 5px;
                      padding: 3px;
                  }
                  QPushButton {
                      background-color: #f4b283;
                      color: black;
                      font-weight: bold;
                      border: 1px solid #c55b26;
                      border-radius: 5px;
                      padding: 6px;
                  }
                  QPushButton:pressed {
                      background-color: #8c3e13;
                  }
              """)

        self.show()  # Ensure the dialog is visible

    def populate_table(self, movement_data):
        """Populates the table widget with test data."""
        try:
            if movement_data and isinstance(movement_data, list):
                self.table.setRowCount(len(movement_data))

                for i, data_item in enumerate(movement_data):
                    test_id = data_item.get('test_id', 'N/A')
                    timestamp = data_item.get('timestamp')
                    last_anxiety_level = data_item.get('anxiety_level')

                    print(f"Original timestamp: {timestamp}")
                    print(f"Type of timestamp: {type(timestamp)}")
                    print(f"Anxiety Level: {last_anxiety_level}")

                    # Initialize formatted timestamp
                    formatted_timestamp = 'Invalid Date'

                    # Format timestamp if it’s a datetime object
                    if isinstance(timestamp, datetime.datetime):
                        formatted_timestamp = timestamp.strftime('%B %d, %Y %H:%M:%S')

                    # Populate table cells
                    self.table.setItem(i, 0, QTableWidgetItem(str(test_id)))
                    self.table.setItem(i, 1, QTableWidgetItem(formatted_timestamp))
                    self.table.setItem(i, 2, QTableWidgetItem(str(data_item.get('movement_amount', 'N/A'))))
                    self.table.setItem(i, 3, QTableWidgetItem(data_item.get('test_result', 'N/A')))
                    self.table.setItem(i, 4, QTableWidgetItem(
                        str(last_anxiety_level)))  # Use anxiety level from the last item

                    # Add a button for notes
                    note_button = QPushButton("View")
                    note_button.clicked.connect(lambda _, index=i: self.handle_note_button_clicked(index))
                    self.table.setCellWidget(i, 5, note_button)  # Adjust column index for button if needed
            else:
                print("No test data available or invalid format.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def handle_note_button_clicked(self, index):
        """Handles the click event of the note buttons."""
        note = self.movement_data[index].get('note', '')
        note_dialog = NoteDialog(note)
        if note_dialog.exec_() == QDialog.Accepted:
            new_note = note_dialog.get_note()
            try:
                self.db.update_note(self.participant_id, index + 1, new_note)
                self.movement_data[index]['note'] = new_note
                self.populate_table(self.movement_data)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update note: {e}")


class MainWindow(FramelessWindow):
    """
    The main window class for the Mock MRI Scanner application.

    Attributes:
        client: The MongoClient object for database operations.
        db: The MovementData object for interacting with the 'movement_data' collection in the database.
        current_test_data: A list to store the current test data.
        collect_movement_data: A boolean flag indicating whether to collect movement data.
        movement_count: The count of detected movements.
        sound_loader: The SoundLoader object for loading and playing sounds.
        sound_channel: The Pygame sound channel for controlling sound playback.
        participant_details_window: The instance of the participantDetailsWindow.
        participant_id: The ID of the selected participant.
        microphone: The MicrophoneRecorder object for recording audio.

    Methods:
        on_sound_loaded: Callback method when the sound is loaded.
        init_ui: Initializes the user interface of the main window.
        create_controls: Creates the buttons and other controls.
        position_controls: Positions the controls in the layout.
        connect_signals: Connects the signals to their respective slot methods.
        show_participant_details: Displays the participant details window.
        handle_participant_id: Handles the received participant ID.
        start_test: Starts collecting movement data.
        stop_test: Stops collecting movement data and saves the test data to the database.
        show_test_history: Displays the test history window.
        show_microphone_error_message: Shows an error message related to the microphone.
        display_results: Displays the test results.
        toggle_sound: Toggles the sound playback.
        adjust_volume: Adjusts the sound volume.
        toggle_microphone: Toggles the microphone recording.
        get_current_date: Get the current date.
        get_current_time: Get the current time.
        update_time: Update the time label.
        closeEvent: Overrides the close event of the main window.
    """

    def __init__(self, participant):
        """Initializes the MainWindow class."""

        super().__init__(title="Examination of the MRI Simulator")  # Modifier le titre de la fenêtre
        from MRI_Test import SoundLoader, MicrophoneRecorder
        self.body_part_label = None
        self.body_part_combobox = None
        self.init_ui()
        self.client = database.get_client()
        db = self.client['MRI_PROJECT']
        movement_data_collection = db['movement_data']
        self.db = database.MovementData(movement_data_collection, db)
        self.current_test_data = []
        self.collect_movement_data = False
        self.movement_count = 0
        pygame.mixer.init()
        self.sound_loader = SoundLoader("../mrisound.mp3")
        self.sound_channel = None
        self.sound_loader.sound_loaded.connect(self.toggle_sound)
        self.sound_loader.start()
        self.sound_channel = None
        self.participant_details_window = None
        self.participant = participant
        self.threshold = None
        self.microphone = MicrophoneRecorder()
        self.bodyPart = None

    def init_ui(self):
        """Initializes the user interface of the main window."""
        # Set main window properties
        from MRI_Test import OpticalFlowApp
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("Main Window")
        self.setGeometry(300, 300, 600, 700)
        self.setWindowFlags(Qt.FramelessWindowHint)
        main_layout = self.layout
        main_layout.setContentsMargins(10, 0, 10, 10)
        self.viewfinder = QLabel(self)
        self.viewfinder.setFrameShape(QFrame.StyledPanel)
        self.viewfinder.setFrameShadow(QFrame.Raised)
        self.viewfinder.setScaledContents(True)
        self.viewfinder.setAlignment(Qt.AlignCenter)
        self.viewfinder.lower()
        main_layout.addWidget(self.viewfinder)

        self.optical_flow_app = OpticalFlowApp(self, self)
        main_layout.addWidget(self.optical_flow_app)

        # Create other widgets and components
        self.create_controls()

        # Add controls to the layout
        controls_layout = QGridLayout()
        controls_layout.setSpacing(2)
        controls_layout.setHorizontalSpacing(10)
        main_layout.addLayout(controls_layout)

        # Position controls as required
        self.position_controls(controls_layout)
        self.connect_signals()
        self.date_label = QLabel(self)
        self.date_label.setText(self.get_current_date())
        self.time_label = QLabel(self)
        self.time_label.setText(self.get_current_time())

        # Layout and styling (optional)
        date_time_layout = QHBoxLayout()
        date_time_layout.addWidget(self.date_label)
        date_time_layout.addWidget(self.time_label)
        date_time_layout.addStretch()  # Add stretch to move labels to the right
        main_layout.addLayout(date_time_layout)

        # Align the date and time labels to the bottom-right corner
        main_layout.addStretch()

        # Update time every second (optional)
        timer = QTimer(self)
        timer.setInterval(1000)  # 1 second
        timer.timeout.connect(self.update_time)
        timer.start()
        self.show()

        self.setStyleSheet("""
                   background-color: #f8cba8;
                   QDialog {
                       background-color: #f8cba8;
                   }
                   QLabel {
                       color: black;
                       font-weight: bold;
                       background-color: #f8cba8;
                   }
                   QLineEdit, QComboBox, QDateEdit {
                       background-color: #fbe5d6;
                       border: 1px solid #c55b26;
                       border-radius: 5px;
                       padding: 3px;
                   }
                   QPushButton {
                       background-color: #f4b283;
                       color: black;
                       font-weight: bold;
                       border: 1px solid #c55b26;
                       border-radius: 5px;
                       padding: 6px;
                   }
                   QPushButton:pressed {
                       background-color: #8c3e13;
                   }
               """)

    def create_controls(self):
        """Creates the buttons and other controls."""
        self.start_test_button = self.create_button("START")
        self.stop_test_button = self.create_button("STOP")

        self.start_test_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.stop_test_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        button_width = 100  # Set your desired width
        button_height = 30  # Set your desired height

        self.start_test_button.setFixedSize(button_width, button_height)
        self.stop_test_button.setFixedSize(button_width, button_height)
        self.start_test_button.setCursor(Qt.PointingHandCursor)
        self.stop_test_button.setCursor(Qt.PointingHandCursor)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_label_text = QLabel("VOLUME")
        self.volume_label_value = QLabel("50")
        self.toggle_microphone_checkbox = QCheckBox()
        self.toggle_microphone_label = QLabel("MICROPHONE 🎙️")
        self.sensitivity_menu = QComboBox()
        self.sensitivity_label = QLabel("Movement Sensitivity:")
        self.movement_detected_result_label = QLabel()
        self.movement_value_label = QLabel("Movement Value:")
        self.movement_detected_label = QLabel("Movement Detected:")
        self.movement_details_label = QLabel("Movement Details")
        self.spacerline = QFrame()
        self.spacerline.setFrameShape(QFrame.HLine)
        self.spacerline.setFrameShadow(QFrame.Sunken)
        self.spacerline.setLineWidth(10)
        self.spacerline.setStyleSheet("color: #2c2f33;")
        self.empty_label = QLabel()
        self.empty_field = QLabel()
        self.movement_details_label.setFont(QFont('Roboto', 12, QFont.Bold, italic=True))
        self.movement_details_label.setStyleSheet("font-size: 12px; text-decoration: underline;")
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(0)
        self.volume_slider.setTickInterval(5)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_label = QLabel("ALLOWABLE DEVIATION")
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(3)
        self.threshold_slider.setTickInterval(1)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.body_part_label = QLabel("SELECT EXAMINATED BODY PART:")  # New label for body part selection
        self.body_part_combobox = QComboBox()  # New combo box for body part selection
        self.body_part_combobox.addItems(["Head", "Hand", "Foot", "Stomach", "Legs", "Arms"])  # Add options
        self.volume_slider.setStyleSheet(
            """
            color: white;
            font-weight: bold;

            QSlider::groove:horizontal {
                border: none;  /* Remove border for a seamless look */
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #e0e0e0, stop:1 #cccccc);
                height: 8px;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: #f0f0f0;  /* Lighter handle background */
                border: 1px solid #cccccc;
                width: 13px;  /* Adjust width for a slimmer handle */
                margin: 2px 0;  /* Adjust for vertical centering */
            }

            /* Optional: Add a subtle shadow effect to the handle */
            QSlider::handle:horizontal {
                qproperty-shadow: 0 1px 1px #aaaaaa;
            }
             QLabel {
                       color: black;
                       font-weight: bold;
                       background-color: #f8cba8;
                   }
            """
        )

    def update_body_part(self, index):
        """Updates the selected body part based on the combobox index."""
        self.bodyPart = self.body_part_combobox.currentText()

    def create_button(self, text):
        """Creates a QPushButton with the specified text."""
        button = QPushButton(text, self)
        button.setStyleSheet("""background-color: #f4b283;
                       color: black;
                       font-weight: bold;
                       border: 1px solid #c55b26;
                       border-radius: 5px;
                       padding: 6px;""")
        button.setFixedWidth(150)
        return button

    def position_controls(self, layout):
        """Positions the controls in the layout."""
        # Adjust the sound layout
        sound_layout = QVBoxLayout()
        sound_layout.setSpacing(0)
        sound_layout.setContentsMargins(0, 0, 0, 0)

        # Sound Label and Slider Layout
        sound_slider_layout = QVBoxLayout()
        sound_slider_layout.addWidget(self.volume_label_value)
        sound_slider_layout.addWidget(self.volume_slider)

        # Microphone Label and Checkbox Layout
        microphone_layout = QVBoxLayout()
        microphone_layout.addWidget(self.toggle_microphone_label)
        microphone_layout.addWidget(self.toggle_microphone_checkbox)

        # Threshold Label and Slider Layout
        threshold_layout = QVBoxLayout()
        threshold_layout.addWidget(self.threshold_label)
        threshold_layout.addWidget(self.threshold_slider)

        # Add each group (label-slider) to sound layout
        sound_layout.addWidget(self.volume_label_text)
        sound_layout.addLayout(sound_slider_layout)
        sound_layout.addLayout(microphone_layout)
        sound_layout.addLayout(threshold_layout)  # Add threshold layout

        # Buttons Layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.start_test_button)
        buttons_layout.addWidget(self.stop_test_button)
        buttons_layout.addStretch()
        buttons_layout.setSpacing(10)

        # Create a layout for the video widget on the right side
        video_layout = QVBoxLayout()
        video_layout.addWidget(self.viewfinder)  # Add viewfinder to the video layout
        video_layout.addStretch()  # Add stretch to align viewfinder to the top

        # Movement Layout
        movement_layout = QVBoxLayout()
        movement_layout.setSpacing(0)
        movement_layout.setContentsMargins(0, 0, 0, 0)
        movement_layout.addWidget(self.movement_detected_result_label)
        movement_layout.addWidget(self.movement_value_label)

        # Body Part Layout
        body_layout = QVBoxLayout()
        body_layout.addWidget(self.body_part_label)
        body_layout.addWidget(self.body_part_combobox)

        # Add controls to the layout
        layout.addLayout(sound_layout, 2, 0)  # Sound controls on the left
        layout.addLayout(body_layout, 3, 0)  # Body part selection below sound controls
        layout.addLayout(buttons_layout, 4, 0)  # Buttons below body part selection
        layout.addLayout(movement_layout, 5, 0)  # Movement details below buttons
        layout.addLayout(video_layout, 0, 1, 6, 1)  # Video widget on the right, spanning multiple rows

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 3)

    def connect_signals(self):
        """Connects the signals to their respective slot methods."""
        self.start_test_button.clicked.connect(self.start_test)
        self.stop_test_button.clicked.connect(self.stop_test)
        self.volume_slider.valueChanged.connect(self.adjust_volume)
        self.toggle_microphone_checkbox.stateChanged.connect(self.toggle_microphone)
        self.body_part_combobox.currentIndexChanged.connect(self.update_body_part)

    def start_test(self):
        """Starts collecting movement data."""
        if self.participant:
            self.collect_movement_data = True
            self.movement_count = 0
            self.threshold = self.threshold_slider.value()  # Update threshold value
            print("Started collecting movement data")
        else:
            QMessageBox.critical(self, "Error", "No participant ID selected.")

    def stop_test(self):
        """Stops collecting movement data and saves the test data to the database."""
        self.collect_movement_data = False
        print("Stopped collecting movement data")

        # if self.current_test_data:
        #    for data in self.current_test_data:
        #        data["participant"] = self.participant

        self.db.save_test_data(self.current_test_data, self.participant, self.bodyPart)

    def show_microphone_error_message(self, message):
        """Shows an error message related to the microphone."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Error")
        msg.setInformativeText(message)
        msg.setWindowTitle("Error")
        msg.exec_()

    def toggle_sound(self):
        """Active ou désactive la lecture du son."""
        state = True  # Mettez ici l'état que vous voulez
        if state:
            if self.sound_channel is None and self.sound_loader.sound:
                self.sound_channel = pygame.mixer.find_channel()
                if self.sound_channel:
                    self.sound_channel.set_volume(self.volume_slider.value() / 100)
                    self.sound_channel.play(self.sound_loader.sound, loops=-1)
        else:
            if self.sound_channel:
                self.sound_channel.stop()
                self.sound_channel = None

    def adjust_volume(self, value):
        """Adjusts the sound volume."""
        if self.sound_channel:
            self.sound_channel.set_volume(value / 100)
        self.volume_label_value.setText(f"{value}")

    def toggle_microphone(self, state):
        """Toggles the microphone recording."""
        if self.microphone.is_microphone_ready():
            if state:
                self.microphone.start()
            else:
                self.microphone.stop()
        else:
            self.show_error_message("No Microphone detected, please connect one and click again.")

    def get_current_date(self):
        today = datetime.date.today()
        return today.strftime("%B %d, %Y")  # Format the date (e.g., March 30, 2024)

    def get_current_time(self):
        now = datetime.datetime.now()
        return now.strftime("%H:%M:%S")  # Format the time (e.g., 23:21:00)

    def update_time(self):
        self.time_label.setText(self.get_current_time())

    def closeEvent(self, event):
        """Overrides the close event of the main window."""
        if self.microphone.recording:
            self.microphone.stop()
            self.microphone.close()
        self.client.close()
        self.optical_flow_app.close()
        event.accept()
