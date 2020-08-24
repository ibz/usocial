## Setting up a venv and creating the database

`python3 -m venv venv`

`source venv/bin/activate`

`pip install --upgrade pip`

`pip install -e .`

```
mkdir instance && cat > instance/config.py << EOF
SECRET_KEY = 'my-key'
SQLALCHEMY_DATABASE_URI = 'sqlite:///db/app.db'
MAIL_SERVER = ''
MAIL_PORT = ''
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
EOF
```

`mkdir mureader/db && python manage.py create_db`

`export FLASK_APP=mureader`

`flask run`

## Building the docker container

`docker build -t ibz/mureader .`

## Running the app in docker

`docker run --rm -it -v $(pwd)/server/db:/db -p 5000:5000 ibz/mureader`
