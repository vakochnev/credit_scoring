# WSGI файл для PythonAnywhere
# Этот файл должен быть размещён в /var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py

import sys
import os

# Добавляем путь к проекту
project_home = os.path.expanduser('~/credit_scoring')
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Активируем виртуальное окружение
activate_this = os.path.expanduser('~/credit_scoring/venv/bin/activate_this.py')
if os.path.exists(activate_this):
    with open(activate_this) as f:
        exec(f.read(), {'__file__': activate_this})

# Импортируем приложение
from app.main import app

application = app

