## Setting up a venv

```
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
```

## Generating a secret key

```
mkdir instance
echo "SECRET_KEY = '"`python3 -c 'import os;print(os.urandom(12).hex())'`"'" > instance/config.py
```

## Creating the database

```
FLASK_APP=musocial.main flask create-db
```

## Running the app locally

`export FLASK_APP=musocial.main`

`flask run`

## Building the Docker container

`docker build -t musocial .`

## Running the app in the Docker container

`docker run -p 8080:80 -v $(pwd)/instance:/instance --name musocial --rm -t musocial`
