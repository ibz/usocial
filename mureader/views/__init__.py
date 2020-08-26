from flask import redirect, url_for

from mureader.views.user import *
from mureader.views.feed import *
from mureader.views.utils import *

from mureader import app

@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('feed.news'))
