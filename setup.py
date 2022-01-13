from setuptools import setup

requirements = None
with open('requirements.txt', 'r') as r:
    requirements = [l.strip() for l in r.readlines()]

setup(
    name='usocial',
    packages=['usocial'],
    include_package_data=True,
    install_requires=requirements,
)
