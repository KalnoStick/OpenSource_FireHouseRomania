import sys
import threading
from flask_app import app
from waitress import serve
from PyQt5.QtWidgets import QApplication
from proiect_cpp import VideoPlayer
import typing_extensions

def run_server():
    serve(app, host='127.0.0.1', port=5000)

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    qt_app = QApplication(sys.argv)
    window = VideoPlayer()
    window.show()
    sys.exit(qt_app.exec_())
