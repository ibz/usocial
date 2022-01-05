Read more at [musocial.me](http://musocial.me).

**WARNING:** musocial is experimental software and may not be ready for use by everyone. Database structure may still change without notice.

## Setting up a venv

```
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
```

## Generating a secret key

(this is required by Flask for [CSRF](https://en.wikipedia.org/wiki/Cross-site_request_forgery) protection)

```
mkdir instance
echo "SECRET_KEY = '"`python3 -c 'import os;print(os.urandom(12).hex())'`"'" > instance/config.py
```

## Creating the database

The database is created in the `instance` directory.

(this will also create the default user, "me", without a password)

```
FLASK_APP=musocial.main flask create-db
```

## Running the app locally

`export FLASK_APP=musocial.main`

`flask run`

## Building the Docker container

`docker build -t musocial .`

## Running the app in the Docker container

NB: We are also mounting the `instance` directory, which contains the database and the config file.

`docker run -p 8080:80 -v $(pwd)/instance:/instance --name musocial --rm -t musocial`
