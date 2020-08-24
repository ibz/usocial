from setuptools import setup

setup(
    name='mureader',
    packages=['mureader'],
    include_package_data=True,
    install_requires=[
        'babel',
        'bs4',
        'feedparser',
        'Flask',
        'Flask-Bcrypt',
        'Flask-Cors',
        'Flask-JWT-Extended',
        'Flask-Mail',
        'Flask-Migrate',
        'Flask-Script',
        'Flask-WTF',
        'itsdangerous',
        'onetimepass',
        'pyjwt',
        'pytest',
        'pyqrcode',
        'requests',
        'wheel',
    ],
)
