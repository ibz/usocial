from setuptools import setup

setup(
    name='ureader',
    packages=['ureader'],
    include_package_data=True,
    install_requires=[
        'Flask',
        'Flask-Bcrypt',
        'Flask-Cors',
        'Flask-JWT-Extended',
        'Flask-Migrate',
        'Flask-Script',
        'Flask-WTF',
        'pyjwt',
        'pytest',
        'wheel',
    ],
)
