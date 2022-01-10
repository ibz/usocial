Read more at [musocial.me](http://musocial.me).

**WARNING:** musocial is experimental software and may not be ready for use by everyone. Database structure may still change without notice.

## Running a pre-built Docker image

The easiest way to run musocial if you have Docker installed is the following:

1. Create an "instance" directory which will store your database and config file.

   `mkdir musocial-instance`
2. Run musocial in a Docker container, forwarding port 8448 (you can change that to anything you want) and mounting the above-created directory.

   `docker run -p 8448:80 -v $(pwd)/musocial-instance:/instance --name musocial --rm -t ibz0/musocial:v0.1.0`
3. Access musocial using your web browser.

   http://localhost:8448

## Running musocial locally

This is slightly more complicated and is recommended only for development.

1. Set up a venv

   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -e .
   ```

2. Create an "instance" directory which will store your database and config file.

   `mkdir instance`
3. Generate a secret key (this is required by Flask for [CSRF](https://en.wikipedia.org/wiki/Cross-site_request_forgery) protection)

   ```echo "SECRET_KEY = '"`python3 -c 'import os;print(os.urandom(12).hex())'`"'" > instance/config.py```
4. Export the environment variables (`FLASK_APP` is required, `FLASK_ENV` makes Flask automatically restart when you edit a file)

   `export FLASK_APP=musocial.main FLASK_ENV=development`
6. Create the database (this will also create the default user, "me", without a password)

   `flask create-db`

5. Run the app locally

   `flask run`
