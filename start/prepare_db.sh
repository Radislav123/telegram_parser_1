cd ..
venv/bin/python manage.py makemigrations telegram_parser
venv/bin/python manage.py migrate
venv/bin/python manage.py create_admin
