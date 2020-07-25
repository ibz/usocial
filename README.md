## Setting up a venv and creating the database

`python3 -m venv venv`

`source venv/bin/activate`

`pip install --upgrade pip`

`pip install -r requirements.txt`

`SQLALCHEMY_DATABASE_URI=sqlite:///db/app.db python manage.py create_db`

## Running the app

`python ./server/run.py`

## Building the docker container

`docker build -t ibz/ureader .`

## Running the app in docker

`docker run --rm -it -v $(pwd)/server/db:/db -p 5000:5000 ibz/ureader`
