from flask_app import app
from waitress import serve
import logger
import logging

"""def run_server():
    serve(app, host='127.0.0.1', port=5000)"""

if __name__ == '__main__':
    serve(app, host='127.0.0.1', port=5000)