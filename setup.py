"""
The Animals API
---------------

Insert very nice description here.
"""
import re
import ast
import setuptools


_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('src/animals/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setuptools.setup(
    name='AnimalsAPI',
    version=version,
    url='https://github.com/appeltel/webservice-animals/',
    license='None',
    author='Eric Appelt',
    author_email='eric.appelt@gmail.com',
    description='A simple and slow API for teaching coroutines',
    long_description=__doc__,
    packages=['animals'],
    package_dir={'': 'src'},
    install_requires=[
        'aioredis',
        'bcrypt',
        'hiredis',
        'sanic',
        'uvloop'
    ],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Education'
    ],
    entry_points='''
        [console_scripts]
        animals=animals.__init__:main
    '''
)
