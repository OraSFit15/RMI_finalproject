import datetime
import sys
import threading
import cv2
import matplotlib.pyplot as plt
import numpy as np
import pyaudio
import pygame
import qt_material
from PyQt5.QtCore import *
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import *
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox, QTableWidgetItem


class CustomDialog(QDialog):
    """A custom dialog window with a title bar."""

    def __init__(self, parent=None, title="My Dialog Title"):
        """Initializes the CustomDialog class.

        Args:
            parent (QWidget): The parent widget (default: None).
            title (str): The title of the dialog (default: "My Dialog Title").
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.title_bar = TitleBar(self, title)
        self.setGeometry(300, 300, 300, 300)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.title_bar)
        self.setLayout(self.main_layout)
        self.title_separator = QFrame(self)
        self.title_separator.setFrameShape(QFrame.HLine)
        self.title_separator.setFrameShadow(QFrame.Sunken)
        self.title_separator.setStyleSheet("background-color: orange;")
        self.main_layout.addWidget(self.title_separator)

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

class TitleBar(QWidget):
    """A custom title bar for the window."""

    def __init__(self, parent, title="Mock MRI"):
        """Initializes the TitleBar class.

        Args:
            parent (QWidget): The parent widget.
            title (str): The title to display on the title bar (default: "Mock MRI").
        """
        super().__init__()
        self.parent = parent
        self.setFixedHeight(30)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.layout.addSpacing(5)
        self.layout.addWidget(QLabel(title, self))
        self.layout.addStretch()

        # Crée les boutons et les stocke comme attributs
        self.minimize_button = TitleButton("-", self)
        self.close_button = TitleButton("X", self)
        self.layout.addWidget(self.minimize_button)
        self.layout.addWidget(self.close_button)

        self.layout.addSpacing(5)
        self.mousePress = None
        self.moveWindow = None
class TitleButton(QPushButton):
    """A custom button for the title bar."""

    def __init__(self, title, parent):
        """Initializes the TitleButton class.

        Args:
            title (str): The title of the button.
            parent (QWidget): The parent widget.
        """
        super().__init__(title, parent)
        self.parent = parent
        self.setFixedWidth(20)
        self.setFixedHeight(20)
        self.clicked.connect(self.clickedEvent)

        self.setStyleSheet("""
            .TitleButton {
                background-color: #f4b283;
                color: black;
                font-weight: bold;
                border: 1px solid #c55b26;
                border-radius: 5px;
                padding: 6px;
            }

    
            .TitleButton:pressed {
                background-color: #8c3e13;

            }
        """)

    def clickedEvent(self):
        """Handles the button's click event."""
        if self.text() == "X":
            self.parent.parent.close()
        elif self.text() == "-":
            self.parent.parent.showMinimized()

