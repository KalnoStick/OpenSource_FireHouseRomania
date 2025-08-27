import sys
from proiect_cpp import StartWindow,AppContainer,LoginWindow,VideoPlayer
from PyQt5.QtWidgets import QApplication
import typing_extensions
import os

if __name__ == '__main__':
    # Start PyQt app from proiect_cpp
    qt_app = QApplication(sys.argv)
    window = VideoPlayer()
    window.show()
    sys.exit(qt_app.exec_())
