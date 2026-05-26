# 📹 Surveilix
***
## About

Surveilix is a full-stack surveillance system that enables real-time monitoring, intelligent alert notifications, and multi-camera management. It employs a client-server architecture where:

- The **client** is a Python desktop application built with PyQt for the UI, using machine learning models for alert detection. It features a modern, interactive interface (UI source files in client/UI/), enabling login, camera selection, and alert email notifications.
- The **server** is a Django web platform deployed on Render, supporting user registration, camera management, and viewing alert frames filtered by camera, email, or date.
- Alert frames and metadata are securely stored on Amazon AWS S3 and PostgreSQL respectively.
- The client application is packaged into a standalone executable using PyInstaller and distributed via a professional installer built with Inno Setup, allowing professional installer experience.

Surveilix’s object detection models are trained using the YOLOv4 architecture in Google Colab. Model training is facilitated by the companion repository [SurveilixTrainingFiles](https://github.com/rohit220604/SurveilixTrainingFiles). The dataset for training is sourced from Kaggle.

**Note:** Pre-trained model files are not included in this repository due to their size—you must manually add the trained model files after training or downloading them separately.

***

## 📌 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation \& Setup](#installation--setup)
    - [Client Side Manual Installation with Pipenv](#client-side-manual-installation-with-pipenv)
    - [Client Side Installation via Setup Executable](#client-side-installation-via-setup-executable)
    - [Server Side Installation (Full Duplication with Pipenv)](#server-side-installation-full-duplication-with-pipenv)
- [Model Training Instructions](#model-training-instructions)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Author \& Contact](#author--contact)

***

## 🚀 Features

- ✅ Desktop client with ML models for alert detection and notifications
- ✅ User registration and login via Django-based server
- ✅ Multi-camera setup, monitoring, and alert management
- ✅ Email alert notifications with direct alert frame links
- ✅ Web dashboard for event and alert management with filtering
- ✅ Alert frame storage on AWS S3
- ✅ Database management via PostgreSQL
- ✅ Server hosted on Render, with client easily installable or runnable from source

***

## 🗂️ Tech Stack

| Layer | Technology |
| :-- | :-- |
| **Client** | Python 3, PyQt (UI), ML models using YOLOv4, PyInstaller (packaging), Inno Setup (installer) |
| **Server** | Django, Django Templates |
| **Database** | PostgreSQL (hosted on Render) |
| **Storage** | Amazon AWS S3 |
| **Deployment** | Render (server/database hosting) |


***

## 🗂️ Project Structure

```
Surveilix/
 ├── client/                  # Python desktop client application
 │    ├── model_files/        # Locally added YOLOv4 trained model files (not included in repo)
 │    ├── main.py             # Python entry point for client app
 │    ├── detection_window.py
 │    ├── login_window.py
 │    ├── detection.py
 │    ├── obj.names         
 │    ├── requirements.txt    # Dependencies for client
 │    ├── Pipfile             # Pipenv environment file for client
 │    ├── Pipfile.lock
 │    ├── UI/                   # Desktop UI source files
 │    └── settings_window.py    # Tool for login inputs and redirect
 ├── server/                  # Django web backend and frontend
 │    ├── alertupload_rest/          
 │        ├── __init__.py
 │        ├── apps.py
 │        ├── serializers.py
 │        ├── tests.py
 │        ├── urls.py
 │        ├── views.py
 │    ├── static/             # Static assets (CSS/fonts/images)
 │    ├── detection/   # Django app: models, views, urls
 │        ├── migrations/
 │        ├── templates/     # Django HTML templates
 │        ├── templatetags/
 │        ├── __init__.py
 │        ├── admin.py
 │        ├── apps.py
 │        ├── filters.py
 │        ├── forms.py
 │        ├── models.py
 │        ├── tests.py
 │        ├── urls.py
 │        ├── views.py
 │    ├── wd_ss/
 │        ├── __init__.py
 │        ├── asgi.py
 │        ├── settings.py
 │        ├── storage_backends.py
 │        ├── urls.py
 │        ├── wsgi.py
 │    ├── .env
 │    ├── Pipfile             # Pipenv environment file for server
 │    ├── Pipfile.lock
 │    ├── requirements.txt 
 │    ├── manage.py           # Django management script
 ├── README.md                # This file
 ├── LICENSE
```


***

## ⚙️ Installation \& Setup


***

### Client Side Manual Installation with Pipenv

To run the client application manually from source (without the installer):

1. **Prerequisites:**
    - Python 3.8+ installed
    - Git (optional to clone)
    - Internet access (for email and server communication)
2. **Clone the repository or download client folder:**

```bash
git clone https://github.com/rohit220604/Surveilix.git
cd Surveilix/client
```

3. **Install and activate pipenv environment:**

```bash
pipenv install
pipenv shell
```

4. **Add your trained YOLOv4 model files manually** into the `client/model_files` directory, as these are not included in the repo.
5. **Run the client:**

```bash
python main.py
```

6. **Workflow:**
    - Login using credentials registered on the web platform
    - Choose camera(s) and input email addresses for alerts
    - Client continuously monitors, sending email alerts with links to the web platform on detections

***

### Client Side Installation via Setup Executable (Quick Install)

You can use the [`SurveilixSetup.exe`](https://drive.google.com/drive/folders/131AVPP4EI2yZkgDRbHbr8SKg74e6pAd8?usp=drive_link) installer located in the `drive` folder for straightforward installation.

1. Click the link above to download the installer from Google Drive.
2. Run the downloaded `SurveilixSetup.exe` file to install the Surveilix client on your system.
3. After installation, launch the client from your desktop or Start menu.
4. Follow the login and setup prompts within the application.

Build Notes:
The standalone executable (Surveilix.exe) was generated from the Python client code using PyInstaller, and the installation setup file (SurveilixSetup.exe) was created using Inno Setup for a professional installer experience.

***

### Server Side Installation (Full Duplication with Pipenv)

1. **Clone the repository or server folder:**

```bash
git clone https://github.com/rohit220604/Surveilix.git
cd Surveilix/server
```

2. **Install dependencies and activate pipenv:**

```bash
pipenv install
pipenv shell
```

3. **Create `.env` in server folder with configuration:**

```
SECRET_KEY=your_django_secret_key
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_STORAGE_BUCKET_NAME=your_s3_bucket_name
DB_NAME=your_database_name
DB_USER=your_database_username
DB_PASSWORD=your_database_password
DB_HOST=your_postgre_sql_link
```

4. **Run database migrations:**

```bash
python manage.py migrate
```

5. **(Optional) Create Django admin user:**

```bash
python manage.py createsuperuser
```

6. **Run the server:**

```bash
python manage.py runserver
```

7. **Access the platform:**
Open http://127.0.0.1:8000/ in your browser.

***

## Model Training Instructions

- Object detection models are built on the **YOLOv4** architecture and have been trained using **Google Colab** for accessible GPU resources.
- The training repository containing data preparation scripts, configuration files, and training notebooks is available at:
[SurveilixTrainingFiles GitHub Repository](https://github.com/rohit220604/SurveilixTrainingFiles)
- The dataset used for training is sourced from Kaggle:
[Kaggle Dataset Link](https://www.kaggle.com/datasets/raghavnanjappan/weapon-dataset-for-yolov5) 
- Because trained model weights are large, **you must manually add the trained model files into the `client/model_files` directory** after downloading or training. The main repository does not include these files to reduce repo size.
- To retrain or update the model, follow the step-by-step instructions in the Google Colab notebook linked below:

**Google Colab Training Notebook:**
[Surveilix YOLOv4 Training on Colab](https://colab.research.google.com/drive/1KZGyMarVVfCkyDo9lfDJS8abKsyIqe1Z)

***

## 🔍 Usage

### Client

- Run client with manual setup or installed executable.
- Log in with server-registered credentials.
- Configure cameras and email addresses.
- Detects alert frames and sends email notifications with clickable links to alert frames on the web platform.


### Server Web Platform

- Register or log in.
- Configure and manage multiple cameras with unique names.
- Filter and browse alert frames by camera, email, and date range.
- Review monitoring history and alerts with security.

***

## 🤝 Contributing

Contributions are warmly welcome!

1. Fork the repository
2. Create your branch: `git checkout -b feature-name`
3. Commit your changes
4. Push and create a pull request

Please keep coding style consistent and add tests if applicable.

***

## 📜 License

This project is licensed under the **MIT License**. See LICENSE for details.

***

## 👤 Author \& Contact

**Rohit Jaliminchi**
GitHub: [https://github.com/rohit220604/Surveilix](https://github.com/rohit220604/Surveilix)

Email: rjrohit2264@gmail.com

***

🚨 **Enjoy secure and intelligent surveillance with Surveilix!**

***