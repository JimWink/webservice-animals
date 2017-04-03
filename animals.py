from sanic import Sanic, Blueprint
from sanic.response import text

from argparse import ArgumentParser
from asyncio import sleep
from base64 import b64decode
from configparser import ConfigParser
from functools import wraps
import ssl

import aioredis
import bcrypt


bp = Blueprint('animals_blueprint')
config = ConfigParser()
pool = None


@bp.listener('before_server_start')
async def setup_redis_pool(app, loop):
    global pool
    try:
        redis_conf = config['redis']
    except KeyError:
        redis_conf = {}
    interface = (
        redis_conf.get('host', 'localhost'),
        int(redis_conf.get('port', 6379))
    )
    sslctx = None
    if redis_conf.get('use_ssl') and redis_conf['use_ssl'].lower() == 'true':
        sslctx = ssl.SSLContext()
        sslctx.load_cert_chain(redis_conf['ssl_cert'])

    pool = await aioredis.create_pool(
        interface,
        minsize=int(redis_conf.get('minsize', 1)),
        maxsize=int(redis_conf.get('maxsize', 10)),
        password=redis_conf.get('password', None),
        ssl=sslctx
    )


@bp.listener('after_server_stop')
async def shutdown_redis_pool(app, loop):
    pool.close()
    await pool.wait_closed()


async def check_auth(username, password):
    async with pool.get() as redis:
        hashed = await redis.connection.execute(
            'hget',
            f'animals:user:{username}', 'hash'
        )

    if hashed is None:
        return False

    return bcrypt.checkpw(password.encode(), hashed)


async def authenticate():
    """Sends a 401 response that enables basic auth"""
    return text(
        'Incorrect credentials with Basic Auth.',
        status=401,
        headers={'WWW-Authenticate': 'Basic realm="Login Required"'}
    )


def requires_auth(f):
    @wraps(f)
    async def decorated(request, *args, **kwargs):
        try:
            auth = b64decode(request.token).decode().split(':')
        except Exception as e:
            return await authenticate()
        if not await check_auth(auth[0], auth[1]):
            return await authenticate()
        return await f(request, *args, **kwargs)
    return decorated


async def check_admin(username):
    async with pool.get() as redis:
        admin = await redis.connection.execute(
            'hget',
            f'animals:user:{username}', 'admin'
        )
    if admin == b'true':
        return True
    return False


async def authorize_admin():
    """Sends a 403 response"""
    return text(
        'Unauthorized action, administrative access required.',
        status=403
    )


def requires_admin(f):
    @wraps(f)
    async def decorated(request, *args, **kwargs):
        try:
            auth = b64decode(request.token).decode().split(':')
        except Exception as e:
            return await authorize_admin()
        if not await check_admin(auth[0]):
            return await authorize_admin()
        return await f(request, *args, **kwargs)
    return decorated


@bp.route('/animals/')
async def hello(request):
    """
    Welcome
    """
    msg = 'Welcome to the farm!'
    return text(msg, status=200)


@bp.route('/animals/<animal>', methods=['GET'])
async def speak(request, animal):
    """
    What does this animal say???
    """
    async with pool.get() as redis:
        val = await redis.connection.execute(
            'get',
            f'animals:item:{animal}'
        )
    if val is None:
        return text('The animal {0} was not found.'.format(animal), status=404)

    await sleep(5)
    return text(val.decode(), status=200)


@bp.route('/animals/<animal>', methods=['PUT'])
@requires_auth
@requires_admin
async def add_animal(request, animal):
    """
    Add an animal to the database
    """
    async with pool.get() as redis:
        await redis.connection.execute(
            'set',
            f'animals:item:{animal}',
            request.body
        )

    return text('Added {0} to the farm'.format(animal), status=201)


@bp.route('/animals/_users/<username>', methods=['POST'])
@requires_auth
@requires_admin
async def update_user(request, username):
    """
    Creates a new user or updates user properties

    Requires a JSON body with admin and password fields
    """
    try:
        password = request.json['password']
        admin = request.json['admin']
    except Exception:
        return text(
            'Request must have a valid json body with a password and '
            'admin field',
            status=400
        )
    async with pool.get() as redis:
        await redis.connection.execute(
            'hmset',
            f'animals:user:{username}',
            'hash', bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
            'admin', admin
        )

    return text('Added user {0}'.format(username), status=201)


if __name__ == "__main__":

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
    app.run(host="127.0.0.1", port=8000, debug=True)
