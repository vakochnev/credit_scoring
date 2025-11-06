# WSGI файл для PythonAnywhere
# Этот файл должен быть размещён в /var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py
#
# ВАЖНО: Замените '~/credit_scoring' на ваш путь к проекту на PythonAnywhere
# Например: '/home/your_username/credit_scoring'

import sys
import os

# Путь к проекту (замените на ваш путь)
# Можно использовать переменную окружения или указать напрямую
project_home = os.environ.get('PROJECT_HOME', os.path.expanduser('~/credit_scoring'))

# Добавляем путь к проекту в sys.path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Активируем виртуальное окружение
venv_path = os.path.join(project_home, 'venv')
activate_this = os.path.join(venv_path, 'bin', 'activate_this.py')

if os.path.exists(activate_this):
    with open(activate_this) as f:
        exec(f.read(), {'__file__': activate_this})
else:
    # Альтернативный способ активации через site-packages
    site_packages = os.path.join(venv_path, 'lib', 'python3.10', 'site-packages')
    if os.path.exists(site_packages) and site_packages not in sys.path:
        sys.path.insert(0, site_packages)

# Загружаем переменные окружения из .env файла (если используется python-dotenv)
try:
    from dotenv import load_dotenv
    env_path = os.path.join(project_home, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    # python-dotenv не установлен, пропускаем
    pass

# Импортируем приложение
try:
    from app.main import app
    application = app
except Exception as e:
    # Логируем ошибку для отладки
    import traceback
    error_log = os.path.join(project_home, 'logs', 'wsgi_error.log')
    os.makedirs(os.path.dirname(error_log), exist_ok=True)
    with open(error_log, 'a') as f:
        f.write(f"WSGI Error: {str(e)}\n")
        f.write(traceback.format_exc())
    raise

