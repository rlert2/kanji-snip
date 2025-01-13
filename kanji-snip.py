import sys
from PyQt5.QtCore import QUrl, Qt
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (QLabel, QPushButton, QVBoxLayout, QLineEdit, QDialog,
                            QAction, QFileDialog, QHBoxLayout, QFormLayout, QCheckBox)
from PIL import Image
from json import JSONDecodeError
import json
import requests
import tkinter as tk
from PIL import ImageGrab
import pytesseract
from PyQt5.QtWebEngineWidgets import QWebEngineView
from googletrans import Translator
import configparser
import io
import os

buffer = io.BytesIO()

class ConfigManager:
    config = configparser.ConfigParser()
    config_file = 'config.ini'

    # creates new config file if missing
    if not os.path.exists(config_file):
        config['Settings'] = {
        'api_key': '',
        'tesseract': 'C:/Program Files/Tesseract-OCR/tesseract.exe'
        }
        with open(config_file, 'w') as file:
            config.write(file)

    config.read(config_file)

    @classmethod
    def get(cls, key):
        try:
            return cls.config.get('Settings', key)
        except configparser.NoSectionError:
            # print("Error: 'Settings' section is missing in the config file.")
            return None
        except configparser.NoOptionError:
            # print(f"Error: The key '{key}' is missing in the 'Settings' section.")
            cls.create_default_config()
            return None
        except Exception as e:
            # print(f"An unexpected error occurred: {e}")
            return None
    
    @classmethod
    def set(cls, api_key, tesseract):
        cls.config['Settings'] = {
            'api_key': api_key,
            'tesseract': tesseract
            }
        with open(cls.config_file, 'w') as file:
            cls.config.write(file)
    
    @classmethod
    def create_default_config(cls):
        cls.config['Settings'] = {
        'api_key': '',
        'tesseract': 'C:/Program Files/Tesseract-OCR/tesseract.exe'
        }
        with open(cls.config_file, 'w') as file:
            cls.config.write(file)

    
class SnippingTool:
    def __init__(self, on_snip_complete):
        self.root = None
        self.canvas = None
        self.on_snip_complete = on_snip_complete

    def start_snip(self):
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.3)
        self.canvas = tk.Canvas(self.root, cursor="cross", bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.root.bind("<ButtonPress-1>", self.on_button_press)
        self.root.bind("<B1-Motion>", self.on_mouse_drag)
        self.root.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.bind("<Escape>", lambda _: self.exit_snip())
        self.root.mainloop()

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_mouse_drag(self, event):
        self.canvas.delete("all")
        self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red", width=2)

    def on_button_release(self, event):
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        self.capture_area(x1, y1, x2, y2)
        self.exit_snip()

    def capture_area(self, x1, y1, x2, y2):
        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))

        # resets buffer
        buffer.seek(0)
        buffer.truncate()

        img.save(buffer, format="PNG")

    def exit_snip(self):
        if self.on_snip_complete:
            self.on_snip_complete()
        self.root.destroy()

class Translation:
        
    def img2text(self):
        image = Image.open(buffer)
        width, height = image.size

        pytesseract.pytesseract.tesseract_cmd = ConfigManager.get('tesseract')

        try:
            if width > height:
                text = pytesseract.image_to_string(image, lang='jpn')
            else:
                text = pytesseract.image_to_string(image, lang='jpn_vert')
                
        except pytesseract.pytesseract.TesseractError as e:
            raise f"Tesseract Error: {str(e)}"
        except pytesseract.TesseractNotFoundError:
            raise Exception("Tesseract OCR not found.")
        except pytesseract.TesseractError as tesseract_err:
            raise Exception(f"Tesseract error occurred: {tesseract_err}")
        except ValueError as value_err:
            raise Exception(f"Value error: {value_err}")
        except RuntimeError as runtime_err:
            raise Exception(f"Runtime error occurred: {runtime_err}")
        except OSError as os_err:
            raise Exception(f"OS error: {os_err}")
        except Exception as err:
            raise Exception(f"An unexpected error occurred: {err}")
        
        text = str(text).strip()

        return text

    def translate(self, text, service_index):
        # Google
        if service_index == 0:
            try:
                output = Translator().translate(text, src='ja', dest='en')
                output = output.text
                return output
            except requests.ConnectionError as e:
                raise Exception (f"Connection error occurred: {e}")
            except requests.Timeout as e:
                raise Exception (f"Timeout error occurred: {e}")
            except requests.exceptions.HTTPError as e:
                raise Exception (f"HTTP error occurred: {e}")
            except JSONDecodeError as e:
                raise Exception (f"JSON decode error occurred: {e}")
            except Exception as e:
                raise Exception (f"Unexpected backend error: {e}")

        #DeepL
        elif service_index == 1:
            url = "https://api-free.deepl.com/v2/translate"
            data = {
                'auth_key': ConfigManager.get('api_key'),
                'text': text,
                'source_lang': 'JA',
                'target_lang': 'EN',
            }

            try:
                response = requests.post(url, data=data)
                output = response.json()['translations'][0]['text']
                return str(output)

            except json.JSONDecodeError:
                if response.status_code == 400:
                    raise Exception ("Bad request. Please check error message and your parameters")
                elif response.status_code == 403:
                    raise Exception ("Authorization failed. Please supply a valid auth_key parameter")
                elif response.status_code == 404:
                    raise Exception ("The requested resource could not be found")
                elif response.status_code == 413:
                    raise Exception ("The request size exceeds the limit")
                elif response.status_code == 414:
                    raise Exception ("Request-URI Too Long")
                elif response.status_code == 429:
                    raise Exception ("Too many requests. Please wait and resend your request")
                elif response.status_code == 456:
                    raise Exception ("Quota exceeded. The character limit has been reached")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 400, 100)
        
        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        
        # API key label
        self.api_key_label = QLabel("API Key:")

        # API key input box
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:xx")
        self.api_key_input.setText(ConfigManager.get('api_key'))

        self.form_layout.addRow(self.api_key_label, self.api_key_input)

        # Browse label
        self.file_label = QLabel("Select File:")

        # Browse text box
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Enter file path or browse...")
        self.file_input.setText(ConfigManager.get('tesseract'))

        # Browse button
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_file)

        # File input and browse button on the same line
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.browse_button)

        self.form_layout.addRow(self.file_label, file_layout)
        
        # save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)

        # cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject) 

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Executable Files (*.exe);;All Files (*)")
        if file_path:
            self.file_input.setText(file_path)

    def save_settings(self):
        ConfigManager.set(self.api_key_input.text(), self.file_input.text())
        self.accept()
        

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kanji Snip")
        self.resize(800, 500)
        self.setStyleSheet(open('style.css').read())

        #initialize classes
        self.snipping_tool = SnippingTool(self.end_snip)
        self.translation = Translation()

        menubar = self.menuBar()
        settings_menu = menubar.addMenu("Settings")

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(settings_action)

        self.centralwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralwidget)
        layout = QtWidgets.QVBoxLayout(self.centralwidget)
        layout.setContentsMargins(20, 10, 20, 10)

        # Selected Text label
        self.SelectedLabel = QtWidgets.QLabel("Selected Text", self.centralwidget)
        layout.addWidget(self.SelectedLabel)

        # Selected Text input box
        self.textbox1 = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.textbox1.setObjectName("TopTextBox")
        self.textbox1.setFixedHeight(150)
        layout.addWidget(self.textbox1)

        # warning for Jisho
        self.warning = QtWidgets.QLabel(self.centralwidget)
        self.warning.setObjectName("warning") 
        self.warning.setVisible(False)
        layout.addWidget(self.warning)

        # appear on top checkbox
        self.ontop_checkbox = QCheckBox("Always on top")
        self.ontop_checkbox.stateChanged.connect(self.toggleAlwaysOnTop)
        layout.addWidget(self.ontop_checkbox)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setContentsMargins(0, 15, 0, 15)
        layout.addLayout(button_layout)

        # drop down box for service select
        self.button1 = QtWidgets.QComboBox(self.centralwidget)
        self.button1.addItems(["Google", "DeepL", "Jisho"])
        self.button1.currentIndexChanged.connect(self.on_combobox_change)
        button_layout.addWidget(self.button1)

        # snip button
        self.button3 = QtWidgets.QPushButton("Snip", self.centralwidget)
        self.button3.clicked.connect(self.start_snip)
        button_layout.addWidget(self.button3)

        # translate button
        self.button2 = QtWidgets.QPushButton("Translate", self.centralwidget)
        self.button2.clicked.connect(self.translate_button)
        button_layout.addWidget(self.button2)

        # snip and translate button
        self.button4 = QtWidgets.QPushButton("Snip and Translate", self.centralwidget)
        self.button4.clicked.connect(self.snip_and_translate)
        button_layout.addWidget(self.button4)

        # Translated Text label
        self.SelectedLabel = QtWidgets.QLabel("Translated Text", self.centralwidget)
        layout.addWidget(self.SelectedLabel)

        # Translated Text box
        self.textbox2 = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.textbox2.setObjectName("BottomTextBox")
        self.textbox2.setFixedHeight(150)
        layout.addWidget(self.textbox2)
        
        self.browser = QWebEngineView()

        layout.addStretch(1)

    def toggleAlwaysOnTop(self, state):
        if state == Qt.Checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def displayWarning(self, text):
        self.warning.setText(text)
        self.warning.setVisible(True)
    
    def clearWarning(self):
        self.warning.setText('')
        self.warning.setVisible(False)
        
    # closes buffer
    def closeEvent(self, event):
        if not buffer.closed:
            buffer.close()
        event.accept()

    def open_settings(self):
        SettingsDialog(self).exec_()

    def on_combobox_change(self, index):
        if index == 2:
            self.displayWarning("NOTE: Jisho only supports looking up words or compount words, not sentences")
        # When switching to DeepL, checks if API Key field is empty or not
        elif index == 1 and not ConfigManager.get('api_key'):
            self.displayWarning("ERROR: DeepL API key not configured")
        else:
            self.clearWarning()

    def start_snip(self):
        self.setWindowOpacity(0)
        QtCore.QTimer.singleShot(500, self.snipping_tool.start_snip)
    
    def end_snip(self):
        self.setWindowOpacity(1)
        self.textbox2.clear()
        try:
            self.textbox1.setPlainText(self.translation.img2text())
        except Exception as e:
            self.displayWarning(f'{e}')

    def translate_button(self):
        self.clearWarning()

        cursor = self.textbox1.textCursor()
        selected_text = cursor.selectedText()
        full_text = self.textbox1.toPlainText()
        
        # index = translation options
        index = self.button1.currentIndex()

        # checks for highlighted text
        if selected_text.strip():
            text = selected_text
        else:
            text = full_text

        # checks if there are any text to translate
        if text.strip():
            layout = self.centralWidget().layout()
            # opens browser window if Jisho is selected
            if index == 2:
                self.browser = QWebEngineView()
                self.browser.setUrl(QUrl(f"https://jisho.org/search/{text}"))
                self.textbox2.setVisible(False)
                layout.addWidget(self.browser)
            # opens translator otherwise
            else:
                if self.browser is not None:
                    self.browser.close()
                self.textbox2.setVisible(True)
                try:
                    self.textbox2.setPlainText(self.translation.translate(text, index))
                except Exception as e:
                    self.displayWarning(f'{e}')
        else:
            self.textbox2.clear()

    def snip_and_translate(self):
        self.setWindowOpacity(0)
        self.snipping_tool.start_snip()
        self.setWindowOpacity(1)
        self.translate_button()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
