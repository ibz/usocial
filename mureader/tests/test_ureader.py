import os
import tempfile

import pytest

from mureader import app, db

@pytest.fixture
def client():
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
        yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])

def register(client, email, password):
    return client.post('/register', data={'email': email, 'password': password}, follow_redirects=True)

def login(client, email, password):
    return client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

def logout(client):
    return client.get('/logout', follow_redirects=True)

def test_login_nouser(client):
    rv = login(client, 'hello@mureader.com', 'hellopass')
    assert b'Incorrect email or password' in rv.data

def test_register(client):
    register(client, 'hello@mureader.com', 'hellopass')
    rv = login(client, 'hello@mureader.com', 'hellopass')
    assert b'Incorrect email or password' not in rv.data
    assert b'Subscribe' in rv.data