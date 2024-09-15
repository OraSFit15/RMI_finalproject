from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QWidget, QPushButton
from RMI_Simulator import database
from RMI_Simulator.database import MongoDB
from RMI_Simulator.GUI import TitleBar


db = MongoDB('MRI_PROJECT', ['USERS', 'PARTICIPANTS', 'movement_data'])

class FramelessWindow(QMainWindow):
    """A frameless window with a title bar."""

    def __init__(self, title=""):
        """Initializes the FramelessWindow class.

        Args:
            title (str): The title of the window (default: "").
        """
        super().__init__()
        self.mousePress = None
        self.moveWindow = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.title_bar = TitleBar(self, title)
        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.addWidget(self.title_bar)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)
        self.title_separator = QFrame(self.central_widget)
        self.title_separator.setGeometry(0, 30, self.width(), 2)
        self.title_separator.setStyleSheet("background-color: #f8cba8;")

        self.setFixedSize(500, 300)

    """def paintEvent(self, event):
        
        painter = QPainter(self)
        pen = QPen(QColor("#cc692f"), 30, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawRect(self.rect())"""

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
class MenuWindow(FramelessWindow):
    def __init__(self):
        """Initializes the Login class."""
        super().__init__(title="Mock MRI Scanner")
        self.stat = None
        self.set = None
        self.exs = None
        self.new = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.label = QLabel("Movement Monitor MRI", self)
        self.label.setGeometry(135, 50, 100, 50)
        self.label.setFixedSize(500, 65)
        self.label.setStyleSheet(
            " font-size: 20px;  color: black;font-weight: bold;"
        )
        self.init_ui()
        self.init_geometry()
        self.client = database.get_client()
        self.db = self.client["MRI_PROJECT"]
        self.user_collection = self.db["USERS"]
        self.users = database.Users(self.user_collection)
        # print(f"user_collection: {self.user_collection}, users: {self.users}")
        # print(self.user_collection.find_one({"username": "admin"}))

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)
        self.layout.addWidget(self.container)

        self.init_new_button()
        self.init_exs_button()
        self.init_stat_button()
        self.init_set_button()
        from RMI_Simulator.Participants import ExistingParticipantDialog
        from RMI_Simulator.Participants import NewParticipantDialog
        from RMI_Simulator.Stats import Statistic
        self.new_participant_dialog = NewParticipantDialog()
        self.existing_participant_dialog = ExistingParticipantDialog()
        self.statistics = Statistic()
        self.show()

    def init_ui(self):
        """Initializes the user interface of the Login window."""
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("Login")

    def close_window(self):
        self.close()

    def init_geometry(self):
        """Sets up the initial geometry of the Login window."""
        self.top = 450
        self.left = 100
        self.width = 550
        self.height = 200
        self.setGeometry(self.top, self.left, self.width, self.height)
        self.setStyleSheet("QWidget { border-radius: 20px;background-color: #f8cba8; }")

    def show_new_participant_dialog(self):
        self.new_participant_dialog.show()

    def show_exs_participant_dialog(self):
        self.existing_participant_dialog.show()

    def show_statistics(self):
        self.statistics.show()

    def init_new_button(self):
        """Initializes the Login button."""
        self.new = QPushButton(self.central_widget)
        self.new.setFixedSize(150, 65)
        self.new.setText("NEW PARTICIPANT")
        self.new.setGeometry(50, 120, 80, 20)
        self.new.setFont(QFont('Roboto', 12))
        self.new.setStyleSheet(
            " border: 1px solid #c55b26; font-size: 12px;"
            " background-color:  #fbe5d6; color: black;font-weight: bold;"
        )
        self.new.setCursor(Qt.PointingHandCursor)

        self.new.clicked.connect(self.show_new_participant_dialog)
        self.new.clicked.connect(self.close_window)

    def init_exs_button(self):
        """Initializes the Login button."""
        self.exs = QPushButton(self.central_widget)
        self.exs.setFixedSize(150, 65)
        self.exs.setText("EXISTING PARTICIPANT")
        self.exs.setGeometry(300, 120, 100, 20)
        self.exs.setFont(QFont('Roboto', 12))
        self.exs.setStyleSheet(
            "  border: 1px solid #c55b26; font-size: 12px;"
            " background-color:  #fbe5d6; color: black;font-weight: bold;"
        )
        self.exs.setCursor(Qt.PointingHandCursor)
        self.exs.clicked.connect(self.show_exs_participant_dialog)
        self.exs.clicked.connect(self.close_window)

    def init_stat_button(self):
        """Initializes the Login button."""
        self.stat = QPushButton(self.central_widget)
        self.stat.setFixedSize(150, 65)
        self.stat.setText("STATISTICS")
        self.stat.setGeometry(50, 200, 80, 20)
        self.stat.setFont(QFont('Roboto', 12))
        self.stat.setStyleSheet(
            "  border: 1px solid #c55b26 ; font-size: 12px;"
            " background-color:  #fbe5d6; color: black;font-weight: bold;"
        )
        self.stat.setCursor(Qt.PointingHandCursor)
        self.stat.clicked.connect(self.show_statistics)
        self.stat.clicked.connect(self.close_window)
        # self.stat.clicked.connect(self.login_clicked)

    def init_set_button(self):
        """Initializes the Login button."""
        self.set = QPushButton(self.central_widget)
        self.set.setFixedSize(150, 65)
        self.set.setText("SETTINGS")
        self.set.setGeometry(300, 200, 80, 20)
        self.set.setFont(QFont('Roboto', 12))
        self.set.setStyleSheet(
            "  border: 1px solid #c55b26 ; font-size: 12px;"
            " background-color:  #fbe5d6; color: black;font-weight: bold;"
        )
        self.set.setCursor(Qt.PointingHandCursor)
        self.set.clicked.connect(self.close_window)
        # self.login.clicked.connect(self.login_clicked)


