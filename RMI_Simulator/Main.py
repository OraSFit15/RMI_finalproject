import sys

import qt_material
from PyQt5.QtWidgets import QApplication

from RMI_Simulator.Login import Login

if __name__ == '__main__':
    print("Executing Main.py...")  # Debugging print statement

    App = QApplication(sys.argv)
    qt_material.apply_stylesheet(App, theme='dark_orange.xml')

    window = Login()
    print("MenuWindow instantiated...")  # Debugging print statement
    sys.exit(App.exec_())
