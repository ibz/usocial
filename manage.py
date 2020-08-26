from flask_script import Manager

from mureader import models
from mureader.main import app, db

manager = Manager(app)

@manager.command
def create_db():
    db.create_all()

@manager.command
def drop_db():
    db.drop_all()

if __name__ == '__main__':
    manager.run()
