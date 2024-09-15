from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QWidget, QPushButton, QMessageBox
from RMI_Simulator import database
from RMI_Simulator.GUI import TitleBar


class Login(QWidget):
    """The login window for the Mock MRI Scanner application."""

    def __init__(self, parent=None, title="MOCK MRI SCANNER"):
        """Initializes the Login class."""
        super().__init__(parent)

        # Create a main layout for the window
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.title_bar = TitleBar(self, title)
        self.password_input = None
        self.appline = None
        self.appname = None
        self.password = None
        self.height = None
        self.width = None
        self.left = None
        self.top = None
        self.login = None
        self.username_input = None
        self.username = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.init_ui()
        self.init_geometry()
        self.client = database.get_client()
        self.db = self.client["MRI_PROJECT"]
        self.user_collection = self.db["USERS"]
        self.users = database.Users(self.user_collection)

        # Create a container widget and its layout for the content
        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setAlignment(Qt.AlignCenter)  # Align the content to the center
        self.container.setLayout(self.container_layout)

        # Add the title bar and container to the main layout
        self.main_layout.addWidget(self.title_bar)
        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)
        self.main_layout.addWidget(self.container)

        # Initialize other UI elements
        self.init_appname()
        self.init_appline()
        self.init_username()
        self.init_password()
        self.init_login_button()

        self.show()

    def init_ui(self):
        """Initializes the user interface of the Login window."""
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("Login")

    def init_geometry(self):
        """Sets up the initial geometry of the Login window."""
        self.top = 450
        self.left = 100
        self.width = 550
        self.height = 200
        self.setGeometry(self.top, self.left, self.width, self.height)
        self.setStyleSheet("""background-color: #f8cba8; """)

    def init_login_button(self):
        """Initializes the Login button."""
        self.login = QPushButton("LOGIN")
        self.login.setFont(QFont('Roboto', 12))
        self.login.setStyleSheet(
            """ QPushButton {""""""
                background-color: #f4b283;
                color: black;
                font-weight: bold;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:pressed {
                background-color: #8c3e13;
            }""")
        self.login.setFixedSize(100, 30)
        self.login.setCursor(Qt.PointingHandCursor)
        self.login.clicked.connect(self.login_clicked)

        self.container_layout.addWidget(self.login)  # Ajouté au layout du conteneur

    def init_username(self):
        """Initializes the Username label and input field."""
        self.username = QLabel("USERNAME:")
        self.username.setStyleSheet(""" color: black;
                       font-weight: bold;
                       background-color: #f8cba8;""")
        self.username_input = QLineEdit()
        self.username_input.setFixedSize(250, 20)
        self.username_input.setStyleSheet(""" color: black;
                font-weight: bold;
                background-color: #f8cba8;""")
        self.username_input.setStyleSheet("""background-color: #fbe5d6;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 3px;""")

        self.container_layout.addWidget(self.username)  # Ajouté au layout du conteneur
        self.container_layout.addWidget(self.username_input)  # Ajouté au layout du conteneur

    def init_password(self):
        """Initializes the Password label and input field."""
        self.password = QLabel("PASSWORD:")
        self.password.setStyleSheet(""" color: black;
                       font-weight: bold;
                       background-color: #f8cba8;""")
        self.password_input = QLineEdit()
        self.password_input.setFixedSize(250, 20)
        self.password_input.setStyleSheet(""" color: black;
                font-weight: bold;
                background-color: #f8cba8;""")
        self.password_input.setStyleSheet("""background-color: #fbe5d6;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 3px;""")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.container_layout.addWidget(self.password)  # Ajouté au layout du conteneur
        self.container_layout.addWidget(self.password_input)  # Ajouté au layout du conteneur

    def init_appname(self):
        """Initializes the application name label."""
        self.appname = QLabel("Welcome, insert your credentials to continue")  # Correction apportée ici
        self.appname.setFont(QFont('Roboto', 12))
        self.appname.setStyleSheet("font-size: 20px;")
        self.container_layout.addWidget(self.appname)  # Ajouté au layout du conteneur

    def init_appline(self):
        """Initializes the horizontal lines below the labels and input fields."""
        self.appline = QFrame()
        self.appline.setGeometry(100, 180, 300, 2)
        self.appline.setStyleSheet("background-color: #f8cbad;")
        self.appline2 = QFrame()
        self.appline2.setGeometry(100, 180, 300, 2)
        self.appline2.setStyleSheet("background-color: #f8cbad;")

    def login_clicked(self):

        """Handles the click event of the Login button."""
        from RMI_Simulator.Menu import MenuWindow
        username = self.username_input.text()
        password = self.password_input.text()

        if self.users.check_user(username, password):
            self.main = MenuWindow()
            self.main.show()
            self.close()
        else:
            QMessageBox.about(self, "Error", "Wrong username or password")

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


