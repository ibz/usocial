## Setting up a venv and creating the database

`python3 -m venv venv`

`source venv/bin/activate`

`pip install --upgrade pip`

`pip install -e .`

```
mkdir instance && cat > instance/config.py << EOF
SECRET_KEY = 'my-key'
SQLALCHEMY_DATABASE_URI = 'sqlite:///../db/app.db'
MAIL_SERVER = ''
MAIL_PORT = ''
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
EOF
```

`mkdir mureader/db && python manage.py create_db`

`export FLASK_APP=mureader.main`

`flask run`

## Building the docker container

`sh build.sh`

## Running the app with docker

Edit `instance/config.py` to set the database URI to `sqlite:////db/app.db` (absolute in this case).

`docker run -p 8080:80 -v $(pwd)/db:/db -v $(pwd)/instance:/instance -t ibz0/mureader`

or

`sh run.sh` to run it on a machine where [docker-compose-letsencrypt-nginx-proxy-companion](https://github.com/evertramos/docker-compose-letsencrypt-nginx-proxy-companion) is already running
