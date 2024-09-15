import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QPushButton

from RMI_Simulator.GUI import TitleBar
from RMI_Simulator.database import MongoDB

db = MongoDB('MRI_PROJECT', ['USERS', 'PARTICIPANTS', 'movement_data'])
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


class Statistic(QDialog):
    """A window for displaying statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statistics")
        self.setGeometry(450, 100, 550, 400)  # Increased height to fit the graph
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.add_stat = AdditionalStat()

        # Main layout
        main_layout = QVBoxLayout()

        # Title bar
        title_bar = TitleBar(self, "STATISTICS")
        main_layout.addWidget(title_bar)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: orange;")
        main_layout.addWidget(separator)

        # Fields layout
        fields_layout = QGridLayout()

        # Number of participants
        num_participants_label = QLabel("Number of Participants:")
        self.num_participants_field = QLineEdit()
        fields_layout.addWidget(num_participants_label, 0, 0)
        fields_layout.addWidget(self.num_participants_field, 0, 1)

        # Gender distribution
        gender_label = QLabel("Gender Distribution:")
        self.female_field = QLineEdit()
        self.female_field.setPlaceholderText("Female")
        self.male_field = QLineEdit()
        self.male_field.setPlaceholderText("Male")
        self.other_field = QLineEdit()
        self.other_field.setPlaceholderText("Other")
        fields_layout.addWidget(gender_label, 1, 0)
        fields_layout.addWidget(self.female_field, 1, 1)
        fields_layout.addWidget(self.male_field, 1, 2)
        fields_layout.addWidget(self.other_field, 1, 3)

        # Average age
        average_age_label = QLabel("Average Age:")
        self.average_age_field = QLineEdit()
        average_from_label = QLabel("From:")
        self.average_age_from_field = QLineEdit()
        average_to_label = QLabel("To:")
        self.average_age_to_field = QLineEdit()
        fields_layout.addWidget(average_age_label, 2, 0)
        fields_layout.addWidget(self.average_age_field, 2, 1)
        fields_layout.addWidget(average_from_label, 2, 2)
        fields_layout.addWidget(self.average_age_from_field, 2, 3)
        fields_layout.addWidget(average_to_label, 2, 4)
        fields_layout.addWidget(self.average_age_to_field, 2, 5)

        average_time_label = QLabel("Average Time:")
        self.average_time_field = QLineEdit()
        max_time_label = QLabel("Max Time:")
        self.max_time_field = QLineEdit()
        min_time_label = QLabel("Min Time:")
        self.min_time_field = QLineEdit()
        fields_layout.addWidget(average_time_label, 3, 0)
        fields_layout.addWidget(self.average_time_field, 3, 1)
        fields_layout.addWidget(max_time_label, 3, 2)
        fields_layout.addWidget(self.max_time_field, 3, 3)
        fields_layout.addWidget(min_time_label, 3, 4)
        fields_layout.addWidget(self.min_time_field, 3, 5)

        # Add fields layout to main layout
        main_layout.addLayout(fields_layout)

        # Additional Stat button
        additional_stat_button = QPushButton("ADDITIONAL STATISTICS")
        additional_stat_button.setCursor(Qt.PointingHandCursor)
        additional_stat_button.clicked.connect(self.show_addstat)
        main_layout.addWidget(additional_stat_button)

        # Button to show statistics
        show_stats_button = QPushButton("SHOW STATISTICS")
        show_stats_button.setCursor(Qt.PointingHandCursor)
        show_stats_button.clicked.connect(self.update_statistics)
        main_layout.addWidget(show_stats_button)

        # Graph layout
        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.graph_layout = QVBoxLayout()
        self.graph_layout.addWidget(self.toolbar)
        self.graph_layout.addWidget(self.canvas)
        main_layout.addLayout(self.graph_layout)

        # Set main layout for dialog
        self.setLayout(main_layout)

        # Stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: #f8cba8;
            }
            QLabel {
                color: black;
                font-weight: bold;
                background-color: #f8cba8;
            }
            QLineEdit {
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

    def show_addstat(self):
        """Show additional statistics."""
        self.add_stat.show()

    def update_statistics(self):
        """Update statistics fields."""
        participants = db.collections['PARTICIPANTS']

        num_participants = participants.count_documents({})
        female_count = participants.count_documents({'sex': 'Female'})
        male_count = participants.count_documents({'sex': 'Male'})
        other_count = participants.count_documents({'sex': 'Other'})

        self.num_participants_field.setText(str(num_participants))
        self.female_field.setText(str(female_count))
        self.male_field.setText(str(male_count))
        self.other_field.setText(str(other_count))

        ages = [doc['age'] for doc in participants.find()]
        if ages:
            avg_age = np.mean(ages)
            min_age = np.min(ages)
            max_age = np.max(ages)
            self.average_age_field.setText(f"{avg_age:.2f}")
            self.average_age_from_field.setText(str(min_age))
            self.average_age_to_field.setText(str(max_age))
        else:
            self.average_age_field.setText("N/A")
            self.average_age_from_field.setText("N/A")
            self.average_age_to_field.setText("N/A")

        # Gender distribution graph
        self.show_gender_distribution()

    def show_gender_distribution(self):
        participants = db.collections['PARTICIPANTS']
        gender_counts = {
            'Female': participants.count_documents({'sex': 'Female'}),
            'Male': participants.count_documents({'sex': 'Male'}),
            'Other': participants.count_documents({'sex': 'Other'})
        }

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.bar(gender_counts.keys(), gender_counts.values(), color='green')
        ax.set_xlabel('Gender')
        ax.set_ylabel('Count')
        ax.set_title('Gender Distribution')
        self.canvas.draw()


class AdditionalStat(QDialog):
    """A window for displaying additional statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Additional Statistics")
        self.setGeometry(450, 100, 700, 500)  # Adjusted size for better layout
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Main layout
        main_layout = QVBoxLayout()

        # Title bar
        title_bar = TitleBar(self, "ADDITIONAL STATISTICS")
        main_layout.addWidget(title_bar)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: orange;")
        main_layout.addWidget(separator)

        # Analysis options
        self.analysis_type = QComboBox()
        self.analysis_type.addItems(["Gender Distribution", "Age Distribution", "Participant Movements"])
        self.analysis_type.currentIndexChanged.connect(self.update_graph)
        main_layout.addWidget(self.analysis_type)

        # Graph layout
        graph_layout = QVBoxLayout()
        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        graph_layout.addWidget(self.toolbar)
        graph_layout.addWidget(self.canvas)
        main_layout.addLayout(graph_layout)

        # Additional buttons
        button_layout = QHBoxLayout()
        button1 = QPushButton("SHOW GRAPHICALLY")
        button1.setCursor(Qt.PointingHandCursor)
        button1.clicked.connect(self.update_graph)
        button2 = QPushButton("SAVE AS PDF")
        button2.setCursor(Qt.PointingHandCursor)
        button2.clicked.connect(self.save_as_pdf)
        button3 = QPushButton("SAVE TO EXCEL")
        button3.setCursor(Qt.PointingHandCursor)
        button3.clicked.connect(self.save_to_excel)
        button_layout.addWidget(button1)
        button_layout.addWidget(button2)
        button_layout.addWidget(button3)
        main_layout.addLayout(button_layout)

        # Set main layout for dialog
        self.setLayout(main_layout)

        # Stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: #f8cba8;
            }
            QLabel {
                color: black;
                font-weight: bold;
                background-color: #f8cba8;
            }
            QLineEdit {
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

        self.current_analysis = None  # Keep track of the current analysis type

    def update_graph(self):
        """Update the graph based on the selected analysis type."""
        self.current_analysis = self.analysis_type.currentText()
        if self.current_analysis == "Gender Distribution":
            self.show_gender_distribution()
        elif self.current_analysis == "Age Distribution":
            self.show_age_distribution()
        elif self.current_analysis == "Participant Movements":
            self.show_participant_movements()

    def show_gender_distribution(self):
        """Display the average movements by gender."""
        participants = db.collections['PARTICIPANTS']
        movements = db.collections['movement_data']

        gender_movements = {'Female': [], 'Male': [], 'Other': []}
        participant_genders = {doc.get('id'): doc.get('sex', 'Other') for doc in participants.find()}

        for movement in movements.find():
            participant_id = movement.get('participant', {}).get('id')
            movement_amount = movement.get('movement_amount', 0)
            gender = participant_genders.get(participant_id, 'Other')
            if gender in gender_movements:
                gender_movements[gender].append(movement_amount)

        avg_gender_movements = {gender: np.mean(movements) if movements else 0
                                for gender, movements in gender_movements.items()}

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.bar(avg_gender_movements.keys(), avg_gender_movements.values(), color='skyblue', edgecolor='black')
        ax.set_xlabel('Gender')
        ax.set_ylabel('Average Movements')
        ax.set_title('Average Movements by Gender')
        ax.grid(True, linestyle='--', alpha=0.7)
        self.canvas.draw()

    def show_age_distribution(self):
        """Display the age distribution graph."""
        participants = db.collections['PARTICIPANTS']
        ages = [doc['age'] for doc in participants.find()]

        if not ages:
            return

        age_bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        age_histogram, _ = np.histogram(ages, bins=age_bins)

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.bar(range(len(age_histogram)), age_histogram,
               tick_label=[f"{age_bins[i]}-{age_bins[i + 1]}" for i in range(len(age_bins) - 1)], color='lightgreen',
               edgecolor='black')
        ax.set_xlabel('Age Range')
        ax.set_ylabel('Count')
        ax.set_title('Age Distribution')
        ax.grid(True, linestyle='--', alpha=0.7)
        self.canvas.draw()

    def show_participant_movements(self):
        """Display the participant movements graph with bars for each participant, showing all movements combined."""
        tests = db.collections['movement_data']

        # Organize data by participant
        participant_movements = {}
        for test in tests.find():
            participant_name = f"{test['participant']['first_name']} {test['participant']['last_name']}"
            movement_amount = test.get('movement_amount', 0)

            if participant_name not in participant_movements:
                participant_movements[participant_name] = []

            participant_movements[participant_name].append(movement_amount)

        # Calculate mean and standard deviation for each participant
        mean_movements = {}
        std_dev_movements = {}
        for participant, movements in participant_movements.items():
            mean_movements[participant] = np.mean(movements)
            std_dev_movements[participant] = np.std(movements, ddof=1)  # Sample standard deviation
            print(std_dev_movements[participant])
        # Plotting
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Prepare data for plotting
        participants = list(mean_movements.keys())
        means = [mean_movements[participant] for participant in participants]
        std_devs = [std_dev_movements[participant] for participant in participants]

        # Plot bars with error bars
        x = np.arange(len(participants))  # X locations for participants
        bar_width = 0.50
        ax.bar(x, means, bar_width, yerr=std_devs, capsize=5, color='skyblue', edgecolor='black')

        # Customizing the plot
        ax.set_xlabel('Participants')
        ax.set_ylabel('Mean Movements')
        ax.set_title('Mean Movements per Participant with Standard Deviation')
        ax.set_xticks(x)
        ax.set_xticklabels(participants)
        plt.xticks(rotation=45, ha='right')
        ax.grid(True, linestyle='--', alpha=0.7)
        self.canvas.draw()

    def save_as_pdf(self):
        """Save the current figure as a PDF."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save as PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.figure.savefig(file_path, format='pdf')

    def save_to_excel(self):
        """Save the current data to an Excel file based on the selected graph."""

        if self.current_analysis == "Gender Distribution":
            self._save_gender_distribution_to_excel()
        elif self.current_analysis == "Age Distribution":
            self._save_age_distribution_to_excel()
        elif self.current_analysis == "Participant Movements":
            self._save_participant_movements_to_excel()

    def _save_gender_distribution_to_excel(self):
        """Save gender distribution data to an Excel file."""
        participants = db.collections['PARTICIPANTS']
        gender_counts = {
            'Female': participants.count_documents({'sex': 'Female'}),
            'Male': participants.count_documents({'sex': 'Male'}),
            'Other': participants.count_documents({'sex': 'Other'})
        }

        df = pd.DataFrame(list(gender_counts.items()), columns=['Gender', 'Count'])
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Gender Distribution as Excel", "",
                                                   "Excel Files (*.xlsx)")
        if file_path:
            df.to_excel(file_path, index=False)

    def _save_age_distribution_to_excel(self):
        """Save age distribution data to an Excel file."""
        participants = db.collections['PARTICIPANTS']
        ages = [doc['age'] for doc in participants.find()]

        if not ages:
            return

        age_bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        age_histogram, _ = np.histogram(ages, bins=age_bins)

        df = pd.DataFrame({
            'Age Range': [f"{age_bins[i]}-{age_bins[i + 1]}" for i in range(len(age_bins) - 1)],
            'Count': age_histogram
        })
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Age Distribution as Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            df.to_excel(file_path, index=False)

    def _save_participant_movements_to_excel(self):
        """Save participant movements data to an Excel file."""
        tests = db.collections['movement_data']
        mean_movements = self._calculate_mean_movements(tests.find())

        df = pd.DataFrame(list(mean_movements.items()), columns=['Participant Name', 'Mean Movements'])
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Participant Movements as Excel", "",
                                                   "Excel Files (*.xlsx)")
        if file_path:
            df.to_excel(file_path, index=False)

    def _calculate_mean_movements(self, movement_data):
        participant_movements = {}

        for doc in movement_data:
            participant_name = f"{doc['participant']['first_name']} {doc['participant']['last_name']}"
            movement_amount = doc.get('movement_amount', 0)

            if participant_name not in participant_movements:
                participant_movements[participant_name] = []

            participant_movements[participant_name].append(movement_amount)

        mean_movements = {name: np.mean(movements) for name, movements in participant_movements.items()}
        return mean_movements
