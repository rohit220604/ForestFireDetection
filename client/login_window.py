from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5.uic import loadUi
from settings_window import SettingsWindow
import webbrowser
import requests
import json

class LoginWindow(QMainWindow):
    def __init__(self):
        super(LoginWindow, self).__init__()
        loadUi('UI/login_window.ui', self)

        self.register_button.clicked.connect(self.go_to_register_page)
        self.login_button.clicked.connect(self.login)

        self.popup = QMessageBox()
        self.popup.setWindowTitle("Failed")
        self.show()

    def go_to_register_page(self):
        webbrowser.open('https://surveilix.onrender.com/register/')
    
    def login(self):
        try:
            url = 'https://surveilix.onrender.com/api/get_auth_token/'
            response = requests.post(url, data={'username': self.username_input.text(),'password': self.password_input.text()})
            json_response = json.loads(response.text)

            if response.ok:
                self.open_settings_window(json_response['token'])
            else:
                self.popup.setText("Username or Password is not correct")
                self.popup.exec_()
        except:
            self.popup.setText("Unable to access server")
            self.popup.exec_()
			
    def open_settings_window(self,token):
        #print("Go to settings page")
        self.setting_window = SettingsWindow(token)
        self.setting_window.displayInfo()
        self.close()