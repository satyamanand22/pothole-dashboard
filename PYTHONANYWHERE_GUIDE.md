# Pothole Dashboard - PythonAnywhere Quick Setup Guide

Use this guide to deploy your app to PythonAnywhere for 100% free with **NO credit card required**.

## Step 1: Create your Free Account
1. Go to **[https://www.pythonanywhere.com/pricing/](https://www.pythonanywhere.com/pricing/)**
2. Click **Create a Beginner account** (the free option on the left).
3. Fill in a username (e.g., `satyapothole`), your email, and a password.
4. Click **Register**. (Your website will be `http://your-username.pythonanywhere.com`).

## Step 2: Open the Cloud Terminal
1. Once logged in, click on the **Consoles** tab at the top.
2. Click on **Bash** under "Start a new console".
3. A black terminal window will open in your browser.

## Step 3: Run the Auto-Setup Script
Copy the entire block of code below, paste it into that black terminal window, and press **Enter**:

```bash
# 1. Download your code from GitHub
git clone https://github.com/satyamanand22/pothole-dashboard.git
cd pothole-dashboard

# 2. Create an isolated Python environment
mkvirtualenv --python=/usr/bin/python3.10 my-env
pip install -r requirements.txt
pip install whitenoise gunicorn

# 3. Setup the database and static files
python manage.py migrate
python manage.py collectstatic --noinput

echo "✅ Code is downloaded and setup!"
```

## Step 4: Turn it On
1. Click the **Web** tab at the top right of the PythonAnywhere page (next to Consoles).
2. Click **Add a new web app**.
3. Click Next, then choose **Manual Configuration** (important!) -> **Python 3.10**.
4. Scroll down to **Virtualenv**: click the red text and type `/home/satyamanand22/.virtualenvs/my-env` (replace `satyamanand22` with your actual PythonAnywhere username).
5. Scroll up to **WSGI configuration file**: click the link (it looks like `/var/www/..._wsgi.py`). Delete all the text in that file and paste this:

```python
import os
import sys

path = '/home/YOUR_USERNAME/pothole-dashboard'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'pothole_system.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
*(Make sure to change `YOUR_USERNAME` in the file!)*

6. Click **Save** (top right) and then the green **Reload** button at the top of the Web page.

## Done!
Your website will now be live at `http://YOUR_USERNAME.pythonanywhere.com`. 
Put that link into your Arduino IDE `SERVER_URL` and flash the ESP32!
