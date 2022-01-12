Read more at [musocial.me](http://musocial.me).

## Running musocial

If you want to just run **musocial** on your laptop, home server or VPS, [check the instructions here](https://musocial.me/running).

If you want to debug or edit the code, keep reading.

## Setting up the development environment

1. Clone the repo

   `git clone https://github.com/ibz/musocial.git && cd musocial`

1. Set up a venv

   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -e .
   ```

1. Create an "instance" directory which will store your database and config file.

   `mkdir instance`
1. Generate a secret key (this is required by Flask for [CSRF](https://en.wikipedia.org/wiki/Cross-site_request_forgery) protection)

   ```echo "SECRET_KEY = '"`python3 -c 'import os;print(os.urandom(12).hex())'`"'" > instance/config.py```
1. Export the environment variables (`FLASK_APP` is required, `FLASK_ENV` makes Flask automatically restart when you edit a file)

   `export FLASK_APP=musocial.main FLASK_ENV=development`
1. Create the database (this will also create the default user, "me", without a password)

   `flask create-db`

1. Run the app locally

   `flask run`
