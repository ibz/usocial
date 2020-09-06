## Setting up a venv and creating the database

`python3 -m venv venv`

`source venv/bin/activate`

`pip install --upgrade pip`

`pip install -e .`

```
mkdir instance && cat > instance/config.py << EOF
SECRET_KEY = 'my-key'
SQLALCHEMY_DATABASE_URI = 'sqlite:///../db/app.db'
EOF
```

`mkdir db && python manage.py create_db`

`export FLASK_APP=musocial.main`

`flask run`

## Building the docker container

`sh build.sh`

## Running the app with docker

```
mkdir instance-docker && cat > instance-docker/config.py << EOF
SECRET_KEY = 'my-key'
SQLALCHEMY_DATABASE_URI = 'sqlite:////db/app.db'
EOF
```

Note that when running locally, we use the config under `instance/` which uses a relative path in the database URI. When running under docker, we use the config under `instance-docker/` which uses an absolute path, because we will mount the database as a volume in docker.

`docker run -p 8080:80 -v $(pwd)/db:/db -v $(pwd)/instance-docker:/instance -t ibz0/musocial`

or

`sh run.sh` to run it on a machine where [docker-compose-letsencrypt-nginx-proxy-companion](https://github.com/evertramos/docker-compose-letsencrypt-nginx-proxy-companion) is already running
