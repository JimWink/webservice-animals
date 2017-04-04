"""
The Animals API

A model slow "RESTful" API for demonstrating
python coroutines that uses sanic, uvloop, and
redis.

Author: Eric Appelt
"""
from sanic import Sanic

from argparse import ArgumentParser
from configparser import ConfigParser

from animals.blueprint import bp


__version__ = '0.0.1a'


def main():
    """
    CLI Entry point to run application
    """
    config = ConfigParser()
    argparser = ArgumentParser()
    argparser.add_argument(
        "-c", "--config",
        help="Specify config file", metavar="FILE"
    )
    args = argparser.parse_args()

    if args.config:
        config.read(args.config)

    app = Sanic(__name__)
    app.blueprint(bp)
    try:
        app.config['redis'] = config['redis']
    except KeyError:
        pass
    app.run(host="127.0.0.1", port=8000, debug=True)
