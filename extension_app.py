from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt5.QtWidgets import QApplication, QMainWindow

class NavBar(QWidget):
    def __init__(self, stack, pages):
        super().__init__()
        self.stack = stack
        self.pages = pages

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.buttons = {}
        for name, widget in pages.items():
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, w=widget: self.switch_to(w))
            layout.addWidget(btn)
            self.buttons[name] = btn

        exit_btn=QPushButton("Exit")
        exit_btn.setStyleSheet("""
                                    QPushButton {
                                        background-color: #b32e2e;
                                        color: white;
                                        padding: 3px 6px;
                                    }""")
        exit_btn.clicked.connect(self.close_app)
        layout.addWidget(exit_btn)

        self.setLayout(layout)

    def switch_to(self, widget):
        self.stack.setCurrentWidget(widget)

    def close_app(self):
        QApplication.quit()

def switch_page(stack_widget, target_widget):
    """
    External function to switch to the given QWidget page.
    """
    stack_widget.setCurrentWidget(target_widget)
