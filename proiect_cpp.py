import sys
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt,QUrl,QTimer
from PyQt5.QtGui import QFont,QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QLineEdit,QHBoxLayout,QMenu,QAction,QFileDialog
from PyQt5.QtWidgets import QStackedWidget, QLineEdit,QFrame,QSizePolicy,QComboBox, QMessageBox,QStackedLayout,QSlider,QTextEdit
from PyQt5.QtGui import QPixmap, QPalette, QBrush,QPainter,QPen
from utlis import resource_path
import pandas as pd
import os
import typing_extensions
import re
from extension_app import NavBar
import requests
import math
import json
import sqlite3
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
import psutil
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import numpy as np
from pyqtgraph.opengl import MeshData
import trimesh
import logger
import logging

try:
    import GPUtil
except ImportError:
    GPUtil = None

class AppContainer(QWidget):
    def __init__(self,user_email=None):
        super().__init__()
        self.user_email = user_email
        #Screen SetUp
        self.setWindowTitle(f'FireHouse_Romania - Logged as {user_email}')
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))
        self.setGeometry(100, 100, 400, 300)

        #Stack Logic
        self.stack = QStackedWidget()

        self.start = StartWindow()
        self.weather = WeatherWindow()
        self.settings = SettingsWindow(user_email=self.user_email)
        self.visualize=VisualizeWindow()

        self.stack.addWidget(self.start)
        self.stack.addWidget(self.weather)
        self.stack.addWidget(self.settings)
        self.stack.addWidget(self.visualize)

        pages = {
            "Home": self.start,
            "Weather": self.weather,
            "Settings": self.settings,
            "Open 3D World Viewer": self.visualize
        }

        # NavBar needs to know which stack it's controlling
        nav = NavBar(self.stack, pages)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack, stretch=1)
        layout.addWidget(nav, stretch=0)  # Nav stays at the bottom

        self.setLayout(layout)

class FullMapWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Set window title and properties for the full map window
        self.setWindowTitle('Google Maps')
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #defaf4;")
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))

        # Create a QWebEngineView to display the map
        self.browser = QWebEngineView()
        # Use the Google Maps URL directly (no API key needed)
        map_url = "https://www.google.com/maps/"
        self.browser.setUrl(QUrl(map_url))

        # Create an Exit button for the full map window
        self.exit_button = QPushButton("Exit", self)
        self.exit_button.setStyleSheet("""
                                    QPushButton {
                                        background-color: #b32e2e;
                                        color: white;
                                        border: none;
                                        padding: 12px 24px;
                                        font-size: 16px;
                                        font-weight: bold;
                                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                        transition: all 0.3s ease;
                                    }""")
        self.exit_button.clicked.connect(self.close)

        # Create a layout for the full map window and add the map
        full_map_layout = QVBoxLayout(self)
        full_map_layout.addWidget(self.browser)
        full_map_layout.addWidget(self.exit_button)  # Add the exit button below the map

        # Set the layout for this window
        self.setLayout(full_map_layout)

class ServerMapWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Server Map View")
        self.setGeometry(150, 150, 900, 600)
        self.setStyleSheet("background-color: #defaf4;")
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))

        self.browser = QWebEngineView()
        if getattr(sys, 'frozen', False):
            url = "https://firehouseromania.com/complete_map"
        else:
            url = "http://127.0.0.1:5000/complete_map"

        self.browser.setUrl(QUrl(url))
        # your server map URL

        self.exit_button = QPushButton("Exit", self)
        self.exit_button.setStyleSheet("""
                                                            QPushButton {
                                                                background-color: #b32e2e;
                                                                color: white;
                                                                border: none;
                                                                padding: 12px 24px;
                                                                font-size: 16px;
                                                                font-weight: bold;
                                                                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                                                transition: all 0.3s ease;
                                                            }""")
        self.exit_button.clicked.connect(self.close)

        server_map_layout = QVBoxLayout(self)
        server_map_layout.addWidget(self.browser)
        server_map_layout.addWidget(self.exit_button)
        self.setLayout(server_map_layout)

class AIMapWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prediced zoned with AI")
        self.setGeometry(150, 150, 900, 600)
        self.setStyleSheet("background-color: #defaf4;")
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))

        self.browser = QWebEngineView()
        if getattr(sys, 'frozen', False):
            url = "https://firehouseromania.com/ai_map"
        else:
            url = "http://127.0.0.1:5000/ai_map"

        self.browser.setUrl(QUrl(url))

        self.exit_button = QPushButton("Exit", self)
        self.exit_button.setStyleSheet("""
                                                            QPushButton {
                                                                background-color: #b32e2e;
                                                                color: white;
                                                                border: none;
                                                                padding: 12px 24px;
                                                                font-size: 16px;
                                                                font-weight: bold;
                                                                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                                                transition: all 0.3s ease;
                                                            }""")
        self.exit_button.clicked.connect(self.close)

        ai_map_layout = QVBoxLayout(self)
        ai_map_layout.addWidget(self.browser)
        ai_map_layout.addWidget(self.exit_button)
        self.setLayout(ai_map_layout)

class StatisticsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Statistics")
        self.setGeometry(150, 150, 900, 600)
        self.setStyleSheet("background-color: #defaf4;")
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))

        self.browser = QWebEngineView()
        if getattr(sys, 'frozen', False):
            url = "https://firehouseromania.com/diagnostics"
        else:
            url = "http://127.0.0.1:5000/diagnostics"

        self.browser.setUrl(QUrl(url))

        self.exit_button = QPushButton("Exit", self)
        self.exit_button.setStyleSheet("""
                                                            QPushButton {
                                                                background-color: #b32e2e;
                                                                color: white;
                                                                border: none;
                                                                padding: 12px 24px;
                                                                font-size: 16px;
                                                                font-weight: bold;
                                                                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                                                transition: all 0.3s ease;
                                                            }""")
        self.exit_button.clicked.connect(self.close)

        ai_map_layout = QVBoxLayout(self)
        ai_map_layout.addWidget(self.browser)
        ai_map_layout.addWidget(self.exit_button)
        self.setLayout(ai_map_layout)

class AboutWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Set window title and properties for the About window
        self.setWindowTitle('About Information')
        self.setGeometry(200, 200, 400, 300)
        self.setStyleSheet("background-color: #defaf4;")
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))
        # Create a layout for the About window
        about_layout = QVBoxLayout(self)

        # Add some labels with the About information
        about_info = [
            "This app is meant to point out the zones with high risk of fire hazard to make the authorities and people act accordingly and to help the environment",
            "This app is built using PyQt5 and Flask Server w/ AJAX API port.",
            "You can visualise danger zones in Romania, related to the fire hazard risk",
            "Developed by: Berbecaru Leonard",
            "Version: Beta 1.0.0_x21"
        ]

        for text in about_info:
            info_label = QLabel(text, self)
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setStyleSheet("""
                font-size: 16px;
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                border-radius: 8px;
                padding: 15px;
                margin: 10px;
            """)
            about_layout.addWidget(info_label)

        # Add a return button
        return_button = QPushButton("Return to Main Menu", self)
        return_button.clicked.connect(self.close)  # Close the About window to go back to the main window
        return_button.setStyleSheet("""
                                    QPushButton {
                                        background-color: #b32e2e;
                                        color: white;
                                        border: none;
                                        padding: 12px 24px;
                                        font-size: 16px;
                                        font-weight: bold;
                                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                        transition: all 0.3s ease;
                                    }""")
        about_layout.addWidget(return_button)

        # Set the layout for the About window
        self.setLayout(about_layout)

class ContactWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Set window title and properties for the About window
        self.setWindowTitle('Contact Information')
        self.setGeometry(200, 200, 400, 300)
        self.setStyleSheet("background-color: #defaf4;")
        self.setWindowIcon(QIcon(resource_path('Assests_image/home_icon_1.jpg')))
        # Create a layout for the About window
        about_layout = QVBoxLayout(self)

        # Add some labels with the About information
        about_info = [
            "For contact email at leonard.berbecaru08@gmail.com",
            "Phone Number:0742925557"
        ]

        for text in about_info:
            info_label = QLabel(text, self)
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setStyleSheet("""
                font-size: 16px;
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                border-radius: 8px;
                padding: 15px;
                margin: 10px;
            """)
            about_layout.addWidget(info_label)

        # Add a return button
        return_button = QPushButton("Return to Main Menu", self)
        return_button.clicked.connect(self.close)  # Close the About window to go back to the main window
        return_button.setStyleSheet("""
                                    QPushButton {
                                        background-color: #b32e2e;
                                        color: white;
                                        border: none;
                                        padding: 12px 24px;
                                        font-size: 16px;
                                        font-weight: bold;
                                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                        transition: all 0.3s ease;
                                    }""")
        about_layout.addWidget(return_button)

        # Set the layout for the About window
        self.setLayout(about_layout)

class NewsWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Set window title and properties for the About window
        self.setWindowTitle('News')
        self.setGeometry(200, 200, 400, 300)
        self.setStyleSheet("background-color: #defaf4;")
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))
        # Create a layout for the About window
        about_layout = QVBoxLayout(self)

        # Add some labels with the About information
        news_info = [
            "Added contact info",
            "Added Flask path",
            "Introduced the new AJAX dynamic map",
            "Introduced new statistics button with dynamic chart"
        ]

        for text in news_info:
            info_label = QLabel(text, self)
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setStyleSheet("""
                font-size: 16px;
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                border-radius: 8px;
                padding: 15px;
                margin: 10px;
            """)
            about_layout.addWidget(info_label)

        # Add a return button
        return_button = QPushButton("Return to Main Menu", self)
        return_button.clicked.connect(self.close)  # Close the About window to go back to the main window
        return_button.setStyleSheet("""
                                    QPushButton {
                                        background-color: #b32e2e;
                                        color: white;
                                        border: none;
                                        padding: 12px 24px;
                                        font-size: 16px;
                                        font-weight: bold;
                                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                        transition: all 0.3s ease;
                                    }""")
        about_layout.addWidget(return_button)

        # Set the layout for the About window
        self.setLayout(about_layout)

class ChooseMapsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Choose Maps')
        self.setGeometry(150, 150, 400, 300)
        self.setStyleSheet("background-color: #defaf4;")
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))

        layout = QVBoxLayout()

        label = QLabel("Select a Map to Open")
        label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # AI Map
        ai_map_button = QPushButton("Graph Map", self)
        ai_map_button.clicked.connect(self.open_ai_map)
        layout.addWidget(ai_map_button)

        # Full Map (was Static Map)
        full_map_button = QPushButton("Google Maps", self)
        full_map_button.clicked.connect(self.open_full_map)
        layout.addWidget(full_map_button)

        # Server Map
        server_map_button = QPushButton("Full Map", self)
        server_map_button.clicked.connect(self.open_server_map)
        layout.addWidget(server_map_button)

        # Exit
        exit_button = QPushButton("Exit", self)
        exit_button.clicked.connect(self.close)
        layout.addWidget(exit_button)

        for btn in [ai_map_button, full_map_button, server_map_button, exit_button]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #287271;
                    color: white;
                    border-radius: 10px;
                    padding: 10px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #1b4f4e;
                }
            """)

        self.setLayout(layout)

    def open_map(self, url):
        import webbrowser
        webbrowser.open(url)

    def open_full_map(self):
        self.full_map_window = FullMapWindow()
        self.full_map_window.show()

    def open_server_map(self):
        self.server_map_window = ServerMapWindow()
        self.server_map_window.show()

    def open_ai_map(self):
        self.ai_map_window = AIMapWindow()
        self.ai_map_window.show()

class StartWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.image_path = resource_path("Assests_image/bk_3_conv.png")  # Path to your background image

        # Check if image loads
        self.pixmap = QPixmap(self.image_path)
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))
        self.initUI()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        if not self.pixmap.isNull():
            painter = QPainter(self)
            painter.drawPixmap(self.rect(), self.pixmap)  # Stretch image to fill window

    def initUI(self):
        # Set window title
        self.setWindowTitle('FireHouse_Romania')

        # Set window size
        self.setGeometry(100, 100, 400, 300)

        # Create a layout to organize widgets
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()

        self.layout=QVBoxLayout()

        # Create a title label
        self.title_label = QLabel('Welcome to Fire House Romania', self)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.title_label, stretch=1)
        font = QFont("Serif", 18, QFont.Bold)
        self.title_label.setFont(font)

        # Create a description label
        self.description_label = QLabel('Choose from the maps below to survey the  zones with high fire risk \n       '
                                        '                              in Romania', self)
        self.description_label.setAlignment(Qt.AlignLeft)
        self.description_label.setIndent(20)
        font = QFont("Roboto Slab", 14)  # Set font family to Arial and font size to 16
        self.description_label.setFont(font)
        left_layout.addWidget(self.description_label, stretch=1)

        # Search bar layout
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search here for detailes view on Romanias' counties...")
        self.search_input.returnPressed.connect(self.handle_search)
        self.search_input.setStyleSheet("""
            QLineEdit {
                height: 40px;
                font-size: 16px;
                padding: 6px;
                border-radius: 8px;
                border: 1px solid #ccc;
            }
        """)
        left_layout.addWidget(self.search_input)

        # Create the menu buttons for the left side
        self.menu_buttons = {}

        # Choose Maps button
        self.menu_buttons['Choose Maps'] = QPushButton("Choose Maps", self)
        self.menu_buttons['Choose Maps'].clicked.connect(self.open_choose_maps)
        self.menu_buttons['Choose Maps'].setStyleSheet("background-color: gray; color: white; width: 120px; height: 40px;")
        self.menu_buttons['Choose Maps'].setStyleSheet("""
                    QPushButton {
        background-color: #31a329;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: bold;
        box-shadow: 0 5px 10px rgba(0, 0, 0, 0.3);
        background-image: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #9e9e9e, stop:1 #616161
        );
    }
    QPushButton:hover {
        background-color: #667;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
    }
    QPushButton:pressed {
        background-color: #445;
        padding-top: 14px;
        padding-bottom: 10px;
        box-shadow: inset 0 4px 8px rgba(0, 0, 0, 0.3);
    }
                """)
        left_layout.addWidget(self.menu_buttons['Choose Maps'])

        # About button
        self.menu_buttons['About'] = QPushButton("About", self)
        self.menu_buttons['About'].clicked.connect(self.show_about)
        self.menu_buttons['About'].setStyleSheet("""
                    QPushButton {
                        background-color: #8ba8b0;
                        color: white;
                        border-radius: 15px;
                        border: none;
                        padding: 12px 24px;
                        font-size: 16px;
                        font-weight: bold;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        transition: all 0.3s ease;
                    }
                    QPushButton:hover {
                        background-color: #438ab0;
                        box-shadow: 0 8px 12px rgba(0, 0, 0, 0.2);
                    }
                    QPushButton:pressed {
                        background-color: #1565C0;
                        box-shadow: inset 0 4px 8px rgba(0, 0, 0, 0.1);
                    }
                """)
        left_layout.addWidget(self.menu_buttons['About'])

        # Statistics button
        self.menu_buttons['Statistics'] = QPushButton("Statistics-Fire Hazard", self)
        self.menu_buttons['Statistics'].clicked.connect(self.show_statistics)
        self.menu_buttons['Statistics'].setStyleSheet("""
                            QPushButton {
                                background-color: #8ba8b0;
                                color: white;
                                border-radius: 15px;
                                border: none;
                                padding: 12px 24px;
                                font-size: 16px;
                                font-weight: bold;
                                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                transition: all 0.3s ease;
                            }
                            QPushButton:hover {
                                background-color: #438ab0;
                                box-shadow: 0 8px 12px rgba(0, 0, 0, 0.2);
                            }
                            QPushButton:pressed {
                                background-color: #1565C0;
                                box-shadow: inset 0 4px 8px rgba(0, 0, 0, 0.1);
                            }
                        """)
        left_layout.addWidget(self.menu_buttons['Statistics'])

        # Contact button
        self.menu_buttons['Contact'] = QPushButton("Contact", self)
        self.menu_buttons['Contact'].clicked.connect(self.show_contact)
        self.menu_buttons['Contact'].setStyleSheet("""
            QPushButton {
                background-color: #8ba8b0;
                color: white;
                border-radius: 15px;
                border: none;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;  /* Transition applied to all states */
            }
            QPushButton:hover {
                background-color: #438ab0;
                box-shadow: 0 8px 12px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background-color: #1565C0;
                box-shadow: inset 0 4px 8px rgba(0, 0, 0, 0.1);
            }
        """)
        left_layout.addWidget(self.menu_buttons['Contact'])

        # News button
        self.menu_buttons['News'] = QPushButton("News", self)
        self.menu_buttons['News'].clicked.connect(self.show_news)
        self.menu_buttons['News'].setStyleSheet("""
            QPushButton {
                background-color: #8ba8b0;
                color: white;
                border-radius: 15px;
                border: none;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;  /* Transition applied to all states */
            }
            QPushButton:hover {
                background-color: #438ab0;
                box-shadow: 0 8px 12px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background-color: #1565C0;
                box-shadow: inset 0 4px 8px rgba(0, 0, 0, 0.1);
            }
        """)
        left_layout.addWidget(self.menu_buttons['News'])

        # Create QWebEngineView to display the map
        self.browser = QWebEngineView()
        if getattr(sys, 'frozen', False):
            map_url = "https://firehouseromania.com/complete_map"
        else:
            map_url = "http://127.0.0.1:5000/complete_map"
        self.browser.setUrl(QUrl(map_url))

        # Create an Exit Button on the right side
        """self.exit_button = QPushButton('Exit', self)
        self.exit_button.clicked.connect(AppContainer.close)  # Connect the button to close the app
        self.exit_button.setFixedWidth(100)  # Set a reasonable width for the exit button
        self.exit_button.setStyleSheet(
                            QPushButton {
                                background-color: #b32e2e;
                                color: white;
                                border: none;
                                padding: 12px 24px;
                                font-size: 16px;
                                font-weight: bold;
                                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                transition: all 0.3s ease;
                            })
        left_layout.addWidget(self.exit_button)"""

        # Set the layout for the window
        main_layout.addLayout(left_layout,stretch=1)
        main_layout.addWidget(self.browser, stretch=2)

        left_layout.addStretch(1)

        # Add the stacked widget to the main layout
        #main_layout.addWidget(self.stacked_widget)

        self.setLayout(main_layout)

    def mouseDoubleClickEvent(self, event):
            # Check if the mouse double-clicked inside the map's area
            if self.browser.geometry().contains(event.pos()):
                # Toggle between normal and fullscreen mode
                if self.isFullScreen():
                    self.showNormal()  # Restores the window to normal size
                else:
                    self.showFullScreen()  # Makes the window full screen
            super().mouseDoubleClickEvent(event)

    def open_choose_maps(self):
        self.choose_maps_window = ChooseMapsWindow()
        self.choose_maps_window.show()

    def show_about(self):
        """Show about information."""
        self.about_window = AboutWindow()
        self.about_window.show()  # Open the new window for About info

    def show_statistics(self):
        """Show about information."""
        self.statistics_window = StatisticsWindow()
        self.statistics_window.show()

    def show_contact(self):
        self.contact_window = ContactWindow()
        self.contact_window.show()

    def show_news(self):
        self.news_window = NewsWindow()
        self.news_window.show()

    def handle_search(self):
        query = self.search_input.text().strip().lower()
        sanitized_query = self.sanitize_input(query)

        if not sanitized_query:
            self.search_input.clear()
            self.search_input.setPlaceholderText("Please enter a valid search term")
            return

        try:
            df = pd.read_csv(resource_path('csv_support/County.csv'))  # Load the CSV
            df['Name'] = df['Name'].str.lower().apply(self.sanitize_input)

            result = df[df['Name'].str.contains(sanitized_query, na=False)]

            if not result.empty:
                lat = result.iloc[0]['Latitude']
                lon = result.iloc[0]['Longitude']

                js_code = f"""
                    centerMap({lat}, {lon});
                """

                self.browser.page().runJavaScript(js_code)
                self.search_input.clear()
                self.search_input.setPlaceholderText("Search here...")
            else:
                self.search_input.clear()
                self.search_input.setPlaceholderText("No such county in database")

        except Exception as e:
            print("Error during search:", e)
            self.search_input.clear()
            self.search_input.setPlaceholderText("An error occurred. Please try again.")

    def sanitize_input(self, input_text):
        sanitized = re.sub(r'[^a-zA-Z0-9_ ]', '', input_text)
        return sanitized

class FireRiskCircle(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._target_risk = 0          # target risk percentage to animate to
        self._current_risk = 0.0       # current animated progress
        self.setMinimumSize(150, 150)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_fill)
        self.timer.start(30)  # animation speed (ms)

        # Optional: frame style if you want a floating panel look
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

    def set_risk(self, risk):
        self._target_risk = max(0, min(100, risk))
        # Optional: reset animation starting from 0 if you want smooth refill
        # self._current_risk = 0
        self.update()

    def animate_fill(self):
        if self._current_risk < self._target_risk:
            self._current_risk += 0.7  # increment progress smoothly
            self.update()
        elif self._current_risk > self._target_risk:
            self._current_risk -= 0.7
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect().adjusted(10, 10, -10, -10)

        # Background circle (light gray)
        painter.setPen(QPen(Qt.lightGray, 12))
        painter.drawEllipse(rect)

        # Progress arc (red) - fills clockwise from top (90 degrees)
        painter.setPen(QPen(Qt.red, 12))
        start_angle = 90 * 16  # 90 degrees, Qt uses 1/16 degree units
        span_angle = int(-self._current_risk / 100 * 360 * 16)  # negative to fill clockwise
        painter.drawArc(rect, start_angle, span_angle)

        # Percentage text in center
        painter.setPen(Qt.black)
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{round(self._current_risk)}%")

class WeatherWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Global Variables
        self.current_layer = "clouds_new"
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()

        # Add a layout at the top
        top_container = QWidget()
        top_container.setFixedHeight(30)
        top_container.setStyleSheet("background-color: lightgray;")  # Thin height, adjust as needed

        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)  # Optional: remove margins
        top_layout.setSpacing(0)

        #QFrame with weather info
        self.weather_pop_up = QFrame(self)
        self.weather_pop_up.setFrameShape(QFrame.StyledPanel)
        self.weather_pop_up.setStyleSheet("background-color: rgba(255, 255, 255, 220); border: 1px solid #ccc; padding: 8px;")
        self.weather_pop_up.setFixedSize(300, 200)
        #self.weather_pop_up.move(self.width() + 410, 10)
        self.weather_pop_up.move(self.width() - self.weather_pop_up.width() + 1400, 40)
        self.weather_pop_up.setVisible(False)

        self.right_layout = QVBoxLayout()

        #QFrame with graph info
        self.fire_panel = QFrame(self)
        self.fire_panel.setFrameShape(QFrame.StyledPanel)
        self.fire_panel.setStyleSheet(
            "background-color: rgba(255, 255, 255, 220); border: 1px solid #ccc; padding: 8px;")
        self.fire_panel.setFixedSize(200, 400)
        self.fire_panel.move(20, 30)
        self.fire_panel.setVisible(False)

        self.left_layout = QVBoxLayout()

        #Logic and elements
        self.graph_label = QLabel("Fire Hazard Risk")
        self.graph_label.setAlignment(Qt.AlignCenter)
        self.left_layout.addWidget(self.graph_label)
        self.circle = FireRiskCircle(self.fire_panel)
        self.left_layout.addWidget(self.circle)

        self.weather_info_label = QLabel("Weather info here")
        self.right_layout.addWidget(self.weather_info_label)

        self.browser = QWebEngineView()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for Romanias' counties for weather and fire risk...")
        self.search_input.returnPressed.connect(self.handle_search)
        self.search_input.setStyleSheet("""
                    QLineEdit {
                        height: 40px;
                        font-size: 16px;
                        padding: 6px;
                        border-radius: 8px;
                        border: 1px solid #ccc;
                    }
                """)
        self.map_mode_selector = QComboBox()
        self.map_mode_selector.addItems([
            "clouds_new",
            "temp_new",
            "precipitation_new",
            "pressure_new",
            "wind_new"
        ])
        self.map_mode_selector.currentTextChanged.connect(self.change_map_mode)

        #Enclosing the layout
        self.fire_panel.setLayout(self.left_layout)
        self.weather_pop_up.setLayout(self.right_layout)
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.map_mode_selector)
        main_layout.addWidget(top_container)
        main_layout.addWidget(self.browser)
        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)
        self.setLayout(main_layout)

        self.load_weather_map()

    def load_weather_map(self):
        mode = self.current_layer

        html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8" />
                    <title>Weather Map</title>
                    <style> html, body, #map {{ height: 100%; margin: 0; }} </style>
                    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
                    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
                </head>
                <body>
                <div id="map"></div>
                <script>
                    var map = L.map('map').setView([45.9432, 24.9668], 7);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                        maxZoom: 18
                    }}).addTo(map);

                     var weatherLayer = L.tileLayer('https://firehouseromania.com/api/weather-tiles/{mode}/{{z}}/{{x}}/{{y}}.png', {{
            opacity: 0.6
                }}).addTo(map);
                    var marker = null;
            function centerMap(lat, lon, zoomLevel) {{
            zoomLevel = zoomLevel || 10;
        map.setView([lat, lon], zoomLevel);
        if (marker) {{
        map.removeLayer(marker);
    }}

    marker = L.marker([lat, lon]).addTo(map);
    }}
                </script>
                </body>
                </html>
                """
        self.browser.setHtml(html,QUrl("about:blank"))

    def handle_search(self):
        query = self.search_input.text().strip().lower()
        sanitized_query = self.sanitize_input(query)

        if not sanitized_query:
            self.search_input.clear()
            self.search_input.setPlaceholderText("Please enter a valid search term")
            return

        try:
            df = pd.read_csv(resource_path('csv_support/County.csv'))  # Load the CSV
            df['Name'] = df['Name'].str.lower().apply(self.sanitize_input)

            result = df[df['Name'].str.contains(sanitized_query, na=False)]

            if not result.empty:
                lat = result.iloc[0]['Latitude']
                lon = result.iloc[0]['Longitude']

                js_code = f"""
                    centerMap({lat}, {lon}, 10);
                """

                self.browser.page().runJavaScript(js_code)
                self.search_input.clear()

                #Show data corresponding on search(weather)
                weather = self.get_weather_data(lat, lon)
                if weather:
                    desc = weather['weather'][0]['description'].capitalize()
                    temp = weather['main']['temp']
                    humidity = weather['main']['humidity']
                    city = weather['name']
                    wind_speed = weather['wind']['speed']
                    self.show_weather_info(city, temp, desc, humidity,wind_speed)
                    self.show_fire_risk_graph(temp,wind_speed,humidity)
                else:
                    self.weather_pop_up.setVisible(False)
                    self.fire_panel.setVisible(False)

                self.search_input.setPlaceholderText("Search here...")
            else:
                self.search_input.clear()
                self.search_input.setPlaceholderText("No such county in database")

        except Exception as e:
            print("Error during search:", e)
            self.search_input.clear()
            self.search_input.setPlaceholderText("An error occurred. Please try again.")

    def sanitize_input(self, input_text):
        sanitized = re.sub(r'[^a-zA-Z0-9_ ]', '', input_text)
        return sanitized

    def get_weather_data(self,lat, lon):
        if getattr(sys, 'frozen', False):
            url = f"https://firehouseromania.com/api/weather?lat={lat}&lon={lon}"
        else:
            url = f"http://127.0.0.1:5000/api/weather?lat={lat}&lon={lon}"
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None

    def resizeEvent(self, event):
        super().resizeEvent(event)

        margin = 10  # Distance from edges

        # Position the weather popup on the right side
        if hasattr(self, 'weather_pop_up') and self.weather_pop_up.isVisible():
            self.weather_pop_up.move(
                self.width() - self.weather_pop_up.width() - margin,
                margin
            )

        # Position the fire risk panel on the left side
        if hasattr(self, 'fire_panel') and self.fire_panel.isVisible():
            self.fire_panel.move(
                margin,
                margin
            )

    def show_weather_info(self, city, temp, desc, humidity,wind_speed):
        self.weather_info_label.setText(f"📍 {city}\n🌡 {temp}°C\n☁️{desc} \n💧 {humidity} \n🍃  {wind_speed} m/s")
        self.weather_pop_up.raise_()
        self.weather_pop_up.setVisible(True)

    def change_map_mode(self, mode):
        self.current_layer = mode
        self.load_weather_map()

    def show_fire_risk_graph(self, temp, wind, humidity):
        # Formula to calculate risk
        risk = (temp * 0.4) + (wind * 0.3) + ((100 - humidity) * 0.3)
        risk = max(0, min(100, risk))
        self.circle.set_risk(risk)
        self.fire_panel.raise_()
        self.fire_panel.setVisible(True)  # Show panel if hidden


CONTINENTS_FIRE_RISK = [
    ("Africa", "high", 0, 20),
    ("Asia", "medium", 40, 100),
    ("Europe", "low", 50, 10),
    ("North America", "medium", 40, -100),
    ("South America", "high", -15, -60),
    ("Australia", "low", -25, 135),
]

FIRE_RISK_ZONES = {
    "low": (0, 1, 0, 1),      # green
    "medium": (1, 1, 0, 1),   # yellow
    "high": (1, 0, 0, 1),     # red
}

def latlon_to_xyz(lat, lon, radius=1):
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    x = radius * np.cos(lat_rad) * np.cos(lon_rad)
    y = radius * np.cos(lat_rad) * np.sin(lon_rad)
    z = radius * np.sin(lat_rad)
    return x, y, z

class VisualizeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()

    def initUi(self):
        self.main_layout=QVBoxLayout()

        self.aux_layout=QHBoxLayout()

        self.view = gl.GLViewWidget()
        self.view.opts['distance'] = 5
        self.view.setSizePolicy(pg.QtWidgets.QSizePolicy.Expanding, pg.QtWidgets.QSizePolicy.Expanding)
        self.aux_layout.addWidget(self.view)


        self.controls = QHBoxLayout()
        self.toggle_btn = QPushButton("Switch to Edit Mode")
        self.toggle_btn.clicked.connect(self.toggle_mode)
        self.controls.addWidget(self.toggle_btn)

        self.import_btn = QPushButton("Import 3D Earth Model (.obj, .stl)")
        self.import_btn.clicked.connect(self.import_model)
        self.controls.addWidget(self.import_btn)

        # Legend label (top-right corner)
        self.legend = QLabel()
        #self.legend.setAlignment(Qt.AlignTop | Qt.AlignRight)
        self.legend.setTextFormat(Qt.RichText)
        self.legend.setStyleSheet(
            """color: white;
            background-color: rgba(0, 0, 0, 0.6);
            padding: 4px 6px;  
            font-weight: bold;
            font-size: 10pt;
            border-radius: 4px;
       """ )
        self.legend.setFixedWidth(180)
        self.legend.setFixedWidth(400)
        #self.legend.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.update_legend()
        self.aux_layout.addWidget(self.legend, alignment=Qt.AlignTop | Qt.AlignRight)

        # States
        self.mode = "object"  # "object" or "edit"
        self.earth = None
        self.continent_extrudes = []
        self.fire_risk_points = []
        self.imported_model = None

        self.main_layout.addLayout(self.aux_layout)
        self.main_layout.addLayout(self.controls)
        self.setLayout(self.main_layout)

        self.draw_earth()
        self.draw_fire_risk_points()

    def update_legend(self):
        text = "Risk-level:" + "\n".join(
            f"<html><br><span style='color:rgb({int(r * 255)}, {int(g * 255)}, {int(b * 255)});'>■</span> {name} - {risk.capitalize()} <br></html>"
            for name, risk, _, _ in CONTINENTS_FIRE_RISK
            for (r, g, b, a) in [FIRE_RISK_ZONES[risk]]
        )
        self.legend.setWordWrap(True)
        self.legend.setText(text)

    def clear_scene(self):
        if self.earth:
            self.view.removeItem(self.earth)
            self.earth = None
        for item in self.fire_risk_points:
            self.view.removeItem(item)
        self.fire_risk_points.clear()
        if self.imported_model:
            self.view.removeItem(self.imported_model)
            self.imported_model = None

    def draw_earth(self):
        self.clear_scene()
        md = gl.MeshData.sphere(rows=80, cols=160, radius=1)
        color = (0.2, 0.4, 0.6, 1) if self.mode == "object" else (0.2, 0.4, 0.6, 0.3)
        shader = 'shaded' if self.mode == "object" else 'balloon'
        drawEdges = False if self.mode == "object" else True

        self.earth = gl.GLMeshItem(meshdata=md, smooth=True, color=color, shader=shader, drawFaces=True, drawEdges=drawEdges)
        self.view.addItem(self.earth)


    def draw_fire_risk_points(self):
        for name, risk, lat, lon in CONTINENTS_FIRE_RISK:
            x, y, z = latlon_to_xyz(lat, lon, radius=1.05)
            color = FIRE_RISK_ZONES[risk]
            md = gl.MeshData.sphere(rows=15, cols=15, radius=0.05)
            sphere = gl.GLMeshItem(meshdata=md, smooth=True, color=color, shader='balloon', drawFaces=True)
            sphere.translate(x, y, z)
            self.fire_risk_points.append(sphere)
            self.view.addItem(sphere)

    def toggle_mode(self):
        if self.mode == "object":
            self.mode = "edit"
            self.toggle_btn.setText("Switch to Object Mode")
        else:
            self.mode = "object"
            self.toggle_btn.setText("Switch to Edit Mode")

        # If imported model exists, update its appearance
        if self.imported_model:
            self.update_imported_model_mode()
        else:
            self.draw_earth()

        for item in self.fire_risk_points:
            self.view.removeItem(item)
        self.fire_risk_points.clear()
        self.draw_fire_risk_points()

    def import_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open 3D Earth Model",
            "",
            "3D Model Files (*.obj *.stl);;All Files (*)"
        )
        if not path:
            return

        ext = path.split('.')[-1].lower()
        try:
            if ext == 'obj':
                md = MeshData.fromOBJ(path)
            elif ext == 'stl':
                mesh = trimesh.load(path)
                vertices = np.array(mesh.vertices)
                faces = np.array(mesh.faces)
                md = MeshData(vertexes=vertices, faces=faces)
            else:
                print("Unsupported file format")
                return
        except Exception as e:
            print("Error loading model:", e)
            return

        self.clear_scene()
        self.imported_model = gl.GLMeshItem(meshdata=md, smooth=True, color=(0.6, 0.7, 0.9, 1), shader='shaded', drawFaces=True)
        self.imported_model.scale(0.01, 0.01, 0.01)  # scale might need adjusting
        self.view.addItem(self.imported_model)

        self.draw_continent_extrudes()
        self.draw_fire_risk_points()

    def update_imported_model_mode(self):
        if not self.imported_model:
            return

        if self.mode == "object":
            self.imported_model.setColor((0.6, 0.7, 0.9, 1))
            self.imported_model.setGLOptions('opaque')
        else:  # edit mode - make semi-transparent + edges visible
            # PyQtGraph doesn't support edges for imported models directly,
            # so we simulate edit mode by reducing opacity
            self.imported_model.setColor((0.6, 0.7, 0.9, 0.3))
            self.imported_model.setGLOptions('translucent')



class SettingsWindow(QWidget):
    def __init__(self,user_email, parent=None):
        super().__init__(parent)
        self.user_email = user_email
        self.initUi()
    def initUi(self):
        self.main_layout=QVBoxLayout()

        self.left_container = QWidget()
        self.left_container.setFixedWidth(400)

        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)  # Optional: remove margins
        self.left_layout.setSpacing(0)

        self.generic_panel = QFrame(self)
        self.generic_panel.setFrameShape(QFrame.StyledPanel)
        self.generic_panel.setStyleSheet(
            "background-color: rgba(255, 255, 255, 220); border: 1px solid #ccc; padding: 8px;")
        self.generic_panel.setFixedSize(900, 500)
        self.generic_panel.move(self.width() - self.generic_panel.width() + 800, 300)
        self.generic_panel.setVisible(False)

        self.generic_layout = QVBoxLayout()
        #Logic
        self.label=QLabel("Settings")
        font = QFont()
        font.setPointSize(17)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.label)

        self.specs_button = QPushButton("App Specs")
        self.specs_button.setFixedWidth(300)
        self.specs_button.setFixedHeight(50)
        self.specs_button.clicked.connect(self.show_specs_widget)
        self.main_layout.addWidget(self.specs_button)

        self.main_layout.addSpacing(20)

        self.account_button = QPushButton("Account")
        self.account_button.setFixedWidth(300)
        self.account_button.setFixedHeight(50)
        self.account_button.clicked.connect(self.show_account_widget)
        self.main_layout.addWidget(self.account_button)

        self.main_layout.addSpacing(20)

        self.terms_button = QPushButton("Terms and service")
        self.terms_button.setFixedWidth(300)
        self.terms_button.setFixedHeight(50)
        self.terms_button.clicked.connect(self.show_terms_panel)
        self.main_layout.addWidget(self.terms_button)

        self.main_layout.addSpacing(20)

        self.license_button = QPushButton("License rights")
        self.license_button.setFixedWidth(300)
        self.license_button.setFixedHeight(50)
        self.license_button.clicked.connect(self.show_license_panel)
        self.main_layout.addWidget(self.license_button)

        self.main_layout.addSpacing(20)

        self.signup_button = QPushButton("Sign Up")
        self.signup_button.setFixedWidth(300)
        self.signup_button.setFixedHeight(50)
        self.signup_button.clicked.connect(self.return_to_login)
        self.main_layout.addWidget(self.signup_button)

        if self.user_email!=None:
            self.signup_button.setEnabled(False)
            self.signup_button.setStyleSheet("color: gray; opacity: 0.4;")
        else:
            self.signup_button.setEnabled(True)

        #Finishes
        #self.left_container.setLayout(self.left_layout)
        self.generic_panel.setLayout(self.generic_layout)
        self.main_layout.addWidget(self.left_container)
        self.setLayout(self.main_layout)

    def show_account_widget(self):
        self.account_window = AccountWindowSettings(user_email=self.user_email)
        self.account_window.show()

    def show_specs_widget(self):
        self.specs_window = SystemSpecsWidget()
        self.specs_window.show()

    def return_to_login(self):
        if self.user_email==None:
            self.login_window = LoginWindow()
            self.login_window.show()

    def show_terms_panel(self):
        if self.generic_panel.isVisible():
            self.generic_panel.setVisible(False)
            return
        self.label=QLabel("""1. Acceptance of Terms
By using this FireHouseRomania, you agree to comply with and be bound by these Terms of Service. If you do not agree to these terms, please do not use the App.

2. Use of the App
The App provides weather information and related services based on publicly available data sources. While we strive to provide accurate and timely information, we do not guarantee the accuracy, completeness, or reliability of the data.

3. User Data and Privacy
To enhance your experience, the App collects certain personal information such as your email, name, and usage preferences. This data is stored securely and used only for the purposes of improving the service, personalizing content, and communicating with you. We do not sell or share your personal information with third parties except as required by law or as described in our Privacy Policy.

4. Data Processing
The weather data and any user-provided data may be processed and analyzed to improve the App’s features and functionalities. Your personal information is handled according to applicable data protection laws and the Privacy Policy.

5. User Responsibilities
You are responsible for maintaining the confidentiality of your account information, including your password. You agree to notify us immediately of any unauthorized use of your account.

6. Limitation of Liability
The App is provided "as is" without warranties of any kind. We are not liable for any direct, indirect, incidental, or consequential damages arising from your use of the App or reliance on weather information.

7. Changes to Terms
We may update these Terms of Service from time to time. Continued use of the App after changes indicates acceptance of the updated terms.

8. Contact
For questions about these Terms or the App, please contact us at leonard.berbecaru08@gmail.com.""")
        while self.generic_layout.count():
            item = self.generic_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.generic_layout.addWidget(self.label)
        self.generic_panel.raise_()
        self.generic_panel.setVisible(True)

    def show_license_panel(self):
        if self.generic_panel.isVisible():
                self.generic_panel.setVisible(False)
                return
        self.label = QLabel("Maps are made using Leaflet.\n\n\n"
                            "Weather gathered with OpenWeather API.\n\n\n"
                            "Used PyQt5 for GUI.\n\n\n"
                            "Ajax and Nginx for server feed content.\n\n\n"
                            "Visit site at www.firehouseromania.com\n\n\n"
                            "This app is protected under Proprietary license. All rights reserved\n")
        while self.generic_layout.count():
            item = self.generic_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.generic_layout.addWidget(self.label)
        self.generic_panel.raise_()
        self.generic_panel.setVisible(True)


class SystemSpecsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Specs")
        self.setFixedSize(500, 400)

        layout = QVBoxLayout()

        self.cpu_label = QLabel("CPU Usage: ...")
        self.cpu_clock_label = QLabel("CPU Clock: ...")
        self.ram_label = QLabel("RAM Usage: ...")
        self.gpu_label = QLabel("GPU Usage: ...")

        layout.addWidget(self.cpu_label)
        layout.addWidget(self.cpu_clock_label)
        layout.addWidget(self.ram_label)
        layout.addWidget(self.gpu_label)

        # Button to show advice
        self.boost_btn = QPushButton("Need Boost")
        self.boost_btn.clicked.connect(self.toggle_advice)
        layout.addWidget(self.boost_btn)

        # Hidden advice textbox
        self.advice_text = QTextEdit()
        self.advice_text.setReadOnly(True)
        self.advice_text.setPlainText(
            "Minimal Hardware necesities for app:/n"
            "1. Windows 10 or 11\n"
            "2. 4 GB RAM\n"
            "3. At least 3 to 5 GB free storage:SSD preferably for app process finalisation\n"
            "4. At least a 9 th gen processor\n\n"
            "Tips to boost your computer performance:\n"
            "- Close unnecessary background apps.\n"
            "- Check for malware or viruses.\n"
            "- Upgrade your RAM if possible.\n"
            "- Use a cooling pad or improve airflow.\n"
            "- Disable startup programs you don’t need.\n"
            "- Keep your OS and drivers updated."
        )
        self.advice_text.hide()
        layout.addWidget(self.advice_text)

        self.setLayout(layout)

        # Timer to update stats every 1 second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

        self.update_stats()

    def toggle_advice(self):
        if self.advice_text.isVisible():
            self.advice_text.hide()
        else:
            self.advice_text.show()

    def update_stats(self):
        # CPU usage %
        cpu_usage = psutil.cpu_percent(interval=None)
        self.cpu_label.setText(f"CPU Usage: {cpu_usage:.1f}%")

        # CPU clock frequency in GHz
        freq = psutil.cpu_freq()
        if freq:
            current_ghz = freq.current / 1000
            self.cpu_clock_label.setText(f"CPU Clock: {current_ghz:.2f} GHz")
        else:
            self.cpu_clock_label.setText("CPU Clock: N/A")

        # RAM usage %
        ram = psutil.virtual_memory()
        self.ram_label.setText(f"RAM Usage: {ram.percent:.1f}%")

        # GPU usage %
        if GPUtil:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_load = gpus[0].load * 100  # 0-1 float → %
                self.gpu_label.setText(f"GPU Usage: {gpu_load:.1f}%")
            else:
                self.gpu_label.setText("GPU Usage: No GPU detected")
        else:
            self.gpu_label.setText("GPU Usage: GPUtil not installed")

class AccountWindowSettings(QWidget):
    def __init__(self, user_email, parent=None):
        super().__init__(parent)
        self.user_email = user_email
        self.setFixedSize(400, 300)
        self.setWindowTitle("Account Details")

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

        # Load user info from DB
        self.user_data = self.load_user_data()

        # Display fields
        self.name_label = QLabel(f"Name: {self.user_data.get('name', '')}")
        self.email_label = QLabel(f"Email: {self.user_email}")
        self.password_label = QLabel(f"Password: {'●' * len(self.user_data.get('password', ''))}")

        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.email_label)
        self.layout.addWidget(self.password_label)

        # Change password toggle button
        self.change_pass_btn = QPushButton("Change Password")
        self.change_pass_btn.clicked.connect(self.toggle_password_change)
        self.layout.addWidget(self.change_pass_btn)

        # Hidden password change area
        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Enter new password")
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setVisible(False)

        self.save_pass_btn = QPushButton("Save")
        self.save_pass_btn.setVisible(False)
        self.save_pass_btn.clicked.connect(self.save_new_password)

        self.layout.addWidget(self.pass_edit)
        self.layout.addWidget(self.save_pass_btn)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close)

        self.delete_btn = QPushButton("Delete Account")
        self.delete_btn.setStyleSheet("color: red;")
        self.delete_btn.clicked.connect(self.delete_account)

        bottom_layout.addWidget(self.exit_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.delete_btn)

        self.layout.addStretch()
        self.layout.addLayout(bottom_layout)

    def load_user_data(self):
        try:
            if getattr(sys, 'frozen', False):
                url = f"https://firehouseromania.com/api/user/{self.user_email}"
            else:
                url = f"http://127.0.0.1:5000/api/user/{self.user_email}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()  # Should return {"name": ..., "password": ...}
            else:
                return {}
        except Exception as e:
            print("Failed to load user data:", e)
            return {}

    def toggle_password_change(self):
        is_visible = self.pass_edit.isVisible()
        self.pass_edit.setVisible(not is_visible)
        self.save_pass_btn.setVisible(not is_visible)

    def save_new_password(self):
        new_pass = self.pass_edit.text().strip()
        if not new_pass:
            QMessageBox.warning(self, "Empty Field", "Please enter a new password.")
            return

        try:
            if getattr(sys, 'frozen', False):
                url = "https://firehouseromania.com/api/update_password"
            else:
                url = "http://127.0.0.1:5000/api/update_password"
            response = requests.post(url, json={
                "email": self.user_email,
                "new_password": new_pass
            })

            if response.status_code == 200:
                self.password_label.setText(f"Password: {'●' * len(new_pass)}")
                self.pass_edit.clear()
                self.pass_edit.setVisible(False)
                self.save_pass_btn.setVisible(False)
                QMessageBox.information(self, "Success", "Password updated successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to update password.")
        except Exception as e:
            QMessageBox.critical(self, "Network Error", str(e))

    def delete_account(self):
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete your account? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                if getattr(sys, 'frozen', False):
                    url = "https://firehouseromania.com/api/delete_account"
                else:
                    url = "http://127.0.0.1:5000/api/delete_account"
                response = requests.delete(url, json={
                    "email": self.user_email
                })

                if response.status_code == 200:
                    QMessageBox.information(self, "Deleted", "Your account has been deleted.")
                    self.close()
                    QApplication.quit()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete account.")
            except Exception as e:
                QMessageBox.critical(self, "Network Error", str(e))

USER_DATA_FILE = "user_data.json"

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Authentication - Fire House Romania")
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))
        self.setFixedSize(400, 300)
        self.init_ui()

    def init_ui(self):
        self.stack = QStackedLayout()

        self.login_widget = self.build_login_form()
        self.signup_widget = self.build_signup_form()

        self.stack.addWidget(self.login_widget)
        self.stack.addWidget(self.signup_widget)

        main_layout = QVBoxLayout()
        main_layout.addLayout(self.stack)
        self.setLayout(main_layout)

    def build_login_form(self):
        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Fire House Romania - Login")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("Email")
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.Password)

        layout.addWidget(self.login_email)
        layout.addWidget(self.login_password)

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.login)
        layout.addWidget(self.login_btn)

        signup_link = QPushButton("Don't have an account? Sign up")
        signup_link.setFlat(True)
        signup_link.setStyleSheet("color: blue; text-decoration: underline;")
        signup_link.clicked.connect(lambda: self.stack.setCurrentWidget(self.signup_widget))
        layout.addWidget(signup_link)

        guest_link = QPushButton("Enter as Guest")
        guest_link.setFlat(True)
        guest_link.setStyleSheet("color: blue; text-decoration: underline;")
        guest_link.clicked.connect(self.enter_as_guest)
        layout.addWidget(guest_link)

        widget.setLayout(layout)
        return widget

    def build_signup_form(self):
        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Sign Up")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        self.signup_name = QLineEdit()
        self.signup_name.setPlaceholderText("Name")

        self.signup_email = QLineEdit()
        self.signup_email.setPlaceholderText("Email")

        self.signup_password = QLineEdit()
        self.signup_password.setPlaceholderText("Password")
        self.signup_password.setEchoMode(QLineEdit.Password)

        self.signup_purpose = QLineEdit()
        self.signup_purpose.setPlaceholderText("Purpose of using the app")

        layout.addWidget(self.signup_name)
        layout.addWidget(self.signup_email)
        layout.addWidget(self.signup_password)
        layout.addWidget(self.signup_purpose)

        signup_btn = QPushButton("Create Account")
        signup_btn.clicked.connect(self.signup)
        layout.addWidget(signup_btn)

        back_link = QPushButton("Back to login")
        back_link.setFlat(True)
        back_link.setStyleSheet("color: blue; text-decoration: underline;")
        back_link.clicked.connect(lambda: self.stack.setCurrentWidget(self.login_widget))
        layout.addWidget(back_link)

        widget.setLayout(layout)
        return widget

    def login(self):
        email = self.login_email.text().strip()
        password = self.login_password.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Incomplete", "Please enter both email and password.")
            return

        try:
            if getattr(sys, 'frozen', False):
                url = "https://firehouseromania.com/login"
            else:
                url = "http://127.0.0.1:5000/login"
            response = requests.post(url, json={
                "email": email,
                "password": password
            })

            if response.status_code == 200:
                name = response.json().get("name")
                QMessageBox.information(self, "Login Successful", f"Welcome {name}")
                self.open_main_app(email)
            else:
                QMessageBox.warning(self, "Error", "Invalid email or password.")
        except requests.exceptions.RequestException:
            QMessageBox.critical(self, "Server Error", "Could not connect to server.")
    """def save_users(self, users):
        with open(USER_DATA_FILE, "w") as f:
            json.dump(users, f, indent=4)"""

    """def login(self):
        email = self.login_email.text().strip()
        password = self.login_password.text().strip()

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
            QMessageBox.warning(self, "Error", "Invalid email or password.")"""

    """def signup(self):
        name = self.signup_name.text().strip()
        email = self.signup_email.text().strip()
        password = self.signup_password.text().strip()
        purpose = self.signup_purpose.text().strip()

        if not all([name, email, password, purpose]):
            QMessageBox.warning(self, "Incomplete", "Please fill in all fields.")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password, purpose) VALUES (?, ?, ?, ?)",
                            (name, email, password, purpose))
            conn.commit()
            QMessageBox.information(self, "Success", "Account created. You can now log in.")
            self.clear_signup_fields()
            self.stack.setCurrentWidget(self.login_widget)
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "Email already registered.")
        finally:
            conn.close()"""

    def signup(self):
            name = self.signup_name.text().strip()
            email = self.signup_email.text().strip()
            password = self.signup_password.text().strip()
            purpose = self.signup_purpose.text().strip()

            if not all([name, email, password, purpose]):
                QMessageBox.warning(self, "Incomplete", "Please fill in all fields.")
                return

            if getattr(sys, 'frozen', False):
                url = "https://firehouseromania.com/signup"
            else:
                url = "http://127.0.0.1:5000/signup"
            response = requests.post(url, json={
                'name': name,
                'email': email,
                'password': password,
                'purpose': purpose
            })
            if response.status_code == 201:
                QMessageBox.information(self, "Success", "Account created.")
                self.clear_signup_fields()
                self.stack.setCurrentWidget(self.login_widget)
            else:
                QMessageBox.warning(self, "Error", response.json().get("error", "Signup failed."))

    def clear_signup_fields(self):
        self.signup_name.clear()
        self.signup_email.clear()
        self.signup_password.clear()
        self.signup_purpose.clear()

    def open_main_app(self, user_email):
        self.main_window = AppContainer(user_email=user_email)
        self.main_window.show()
        self.close()
    
    def enter_as_guest(self):
        self.main_window = AppContainer(user_email=None)
        self.main_window.show()
        self.close()

class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(resource_path('Assests_image/Deploy_LOGO.ico')))
        self.setWindowTitle("Fire House Romania")
        self.setGeometry(100, 100, 800, 600)

        # Video widget
        self.video_widget = QVideoWidget()

        # Media player
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)

        # Full path to your .avi file
        video_path = resource_path("Assests_image/FINALVIDEO.avi")  # ← Update this path
        video_url = QUrl.fromLocalFile(video_path)
        self.media_player.setMedia(QMediaContent(video_url))
        self.media_player.setVolume(100)

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_widget)
        self.setLayout(layout)

        self.media_player.mediaStatusChanged.connect(self.handle_media_status)

        # Play video
        self.media_player.play()

    def handle_media_status(self, status):
        from PyQt5.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.EndOfMedia:
            self.media_player.stop()
            self.close()  # close video player window
            self.open_next_widget()
    def open_next_widget(self):
        self.login_window = LoginWindow()
        self.login_window.show()

    def mousePressEvent(self, event):
        # Stop video and close window when clicked
        self.media_player.stop()
        self.close()
        self.login_window = LoginWindow()
        self.login_window.show()

# Main function to run the app
if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    ex = LoginWindow()
    ex.show()
    sys.exit(app.exec_())



