import sys
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QStackedWidget, QFrame
from PyQt5.QtWebEngineWidgets import QWebEngineView


class FullMapWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Set window title and properties for the full map window
        self.setWindowTitle('Full Map')
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #defaf4;")

        # Create a QWebEngineView to display the map
        self.browser = QWebEngineView()
        # Use the Google Maps URL directly (no API key needed)
        map_url = "https://www.google.com/maps/@40.748817,-73.985428,14z"  # Example: New York coordinates
        self.browser.setUrl(QUrl(map_url))

        # Create an Exit button for the full map window
        self.exit_button = QPushButton("Exit", self)
        self.exit_button.clicked.connect(self.close)  # Connect the button to close the map window

        # Create a layout for the full map window and add the map and exit button
        full_map_layout = QVBoxLayout(self)
        full_map_layout.addWidget(self.browser)
        full_map_layout.addWidget(self.exit_button)  # Add the exit button below the map

        # Set the layout for this window
        self.setLayout(full_map_layout)


class StartWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize the UI
        self.initUI()

    def initUI(self):
        # Set window title
        self.setWindowTitle('AI App Start Screen')

        # Set window size
        self.setGeometry(100, 100, 400, 300)
        self.setStyleSheet("background-color: #defaf4;")

        # Create a layout to organize widgets
        self.main_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()  # Create a QStackedWidget to manage different pages/views in the main window
        self.stacked_widget = QStackedWidget(self)

        # Create a title label
        self.title_label = QLabel('Welcome to the AI App', self)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.left_layout.addWidget(self.title_label, stretch=1)

        # Create a description label
        self.description_label = QLabel('This app uses AI to process your input and provide results.', self)
        self.description_label.setAlignment(Qt.AlignLeft)
        self.description_label.setIndent(20)
        font = QFont("Arial", 14)  # Set font family to Arial and font size to 16
        self.description_label.setFont(font)
        self.left_layout.addWidget(self.description_label, stretch=1)

        # Create the menu buttons for the left side
        self.menu_buttons = {}

        # Full Map button
        self.menu_buttons['Full Map'] = QPushButton("Full Map", self)
        self.menu_buttons['Full Map'].clicked.connect(self.open_full_map)
        self.menu_buttons['Full Map'].setStyleSheet("background-color: gray; color: white; width: 120px; height: 40px;")
        self.left_layout.addWidget(self.menu_buttons['Full Map'])

        # About button
        self.menu_buttons['About'] = QPushButton("About", self)
        self.menu_buttons['About'].clicked.connect(self.show_about)
        self.menu_buttons['About'].setStyleSheet("background-color: gray; color: white; width: 120px; height: 40px;")
        self.left_layout.addWidget(self.menu_buttons['About'])

        # Contact button
        self.menu_buttons['Contact'] = QPushButton("Contact", self)
        self.menu_buttons['Contact'].clicked.connect(self.show_contact)
        self.menu_buttons['Contact'].setStyleSheet("background-color: gray; color: white; width: 120px; height: 40px;")
        self.left_layout.addWidget(self.menu_buttons['Contact'])

        # News button
        self.menu_buttons['News'] = QPushButton("News", self)
        self.menu_buttons['News'].clicked.connect(self.show_news)
        self.menu_buttons['News'].setStyleSheet("background-color: gray; color: white; width: 120px; height: 40px;")
        self.left_layout.addWidget(self.menu_buttons['News'])

        # Create an Exit Button
        self.exit_button = QPushButton('Exit', self)
        self.exit_button.clicked.connect(self.close)  # Connect the button to close the app
        self.exit_button.setFixedWidth(100)  # Set a reasonable width for the exit button
        self.left_layout.addWidget(self.exit_button)

        # Set the layout for the window
        self.main_layout.addLayout(self.left_layout, stretch=1)
        self.main_layout.addWidget(self.stacked_widget, stretch=2)

        # Set the layout for the main window
        self.setLayout(self.main_layout)

    def open_full_map(self):
        """Open the full map in a new window."""
        # Create the FullMapWindow instance and show it
        self.full_map_window = FullMapWindow()
        self.full_map_window.show()  # Open the new window with the map

    def show_about(self):
        """Show about information and replace the current interface."""
        # Remove the current layout (main_layout and left_layout)
        for i in reversed(range(self.left_layout.count())):
            widget = self.left_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Create an About section widget with styled boxes
        about_section = QWidget(self)
        about_layout = QVBoxLayout(about_section)

        # Create a return button
        return_button = QPushButton("Return to Main Menu", self)
        return_button.clicked.connect(self.return_to_main_menu)

        # Create the styled boxes (QFrame) to display information
        about_info = [
            "This app is built using PyQt5 and Google Maps API.",
            "It uses AI to process your input and display results.",
            "Developed by: Your Name",
            "Version: 1.0.0"
        ]

        for text in about_info:
            info_box = QFrame(self)
            info_box.setStyleSheet("""
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                border-radius: 8px;
                padding: 15px;
                margin: 10px;
            """)
            info_label = QLabel(text, self)
            info_label.setAlignment(Qt.AlignCenter)
            info_box_layout = QVBoxLayout(info_box)
            info_box_layout.addWidget(info_label)
            about_layout.addWidget(info_box)

        # Add the return button at the bottom of the About section
        about_layout.addWidget(return_button)

        # Set the layout for the About section
        about_section.setLayout(about_layout)

        # Replace the current screen with the About section
        self.stacked_widget.addWidget(about_section)
        self.stacked_widget.setCurrentWidget(about_section)

    def return_to_main_menu(self):
        """Return to the main menu."""
        # Clear the current layout (remove the About section)
        for i in reversed(range(self.stacked_widget.count())):
            widget = self.stacked_widget.widget(i)
            if widget is not None:
                widget.deleteLater()

        # Rebuild the main menu
        self.initUI()  # Call initUI again to rebuild the entire interface

    def show_contact(self):
        """Show contact information."""
        print("Contact: For inquiries, please contact support@example.com.")

    def show_news(self):
        """Show the latest news."""
        print("News: AI App has been updated with new features.")


# Main function to run the app
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = StartWindow()
    ex.show()
    sys.exit(app.exec_())


#python proiect_cpp.py
