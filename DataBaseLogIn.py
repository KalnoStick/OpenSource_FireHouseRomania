import sqlite3
from PyQt5.QtWidgets import QMessageBox
import sys
import os

base_dir=os.path.abspath(".")

os.makedirs(base_dir, exist_ok=True)
DB_FILE = os.path.join(base_dir, "users.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            purpose TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def login(self,email,password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, password FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row and row[1] == password:
        name = row[0]
        QMessageBox.information(self, "Login Successful", f"Welcome {name}")
        self.open_main_app(email)
    else:
        QMessageBox.warning(self, "Error", "Invalid email or password.")