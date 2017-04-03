from sanic import Sanic
from sanic.response import text

from base64 import b64decode
from functools import wraps

from asyncio import sleep, Lock

import aioredis
import bcrypt


class RedisPoolSingleton:
    """
    Wrapper to provide the same redis connection pool to all handlers
    """
    def __init__(self):
        self._redis = None
        self._lock = Lock()
        self._ready = False

    async def get_pool(self):
        if self._ready:
            return self._redis

        await self._lock.acquire()
        try:
            if not self._ready:
                self._redis = await aioredis.create_pool(
                    ('localhost', 6379),
                    minsize=5,
                    maxsize=10
                )
                self._ready = True
        finally:
            self._lock.release()

        return self._redis


app = Sanic(__name__)

rp = RedisPoolSingleton()


async def check_auth(username, password):
    pool = await rp.get_pool()
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
    pool = await rp.get_pool()
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


@app.route('/animals/')
async def hello(request):
    """
    Welcome
    """
    msg = 'Welcome to the farm!'
    return text(msg, status=200)


@app.route('/animals/<animal>', methods=['GET'])
async def speak(request, animal):
    """
    What does this animal say???
    """
    pool = await rp.get_pool()
    async with pool.get() as redis:
        val = await redis.connection.execute(
            'get',
            f'animals:item:{animal}'
        )
    if val is None:
        return text('The animal {0} was not found.'.format(animal), status=404)

    await sleep(5)
    return text(val.decode(), status=200)


@app.route('/animals/<animal>', methods=['PUT'])
@requires_auth
@requires_admin
async def add_animal(request, animal):
    """
    Add an animal to the database
    """
    pool = await rp.get_pool()
    async with pool.get() as redis:
        await redis.connection.execute(
            'set',
            f'animals:item:{animal}',
            request.body
        )

    return text('Added {0} to the farm'.format(animal), status=201)


@app.route('/animals/_users/<username>', methods=['POST'])
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
    pool = await rp.get_pool()
    async with pool.get() as redis:
        await redis.connection.execute(
            'hmset',
            f'animals:user:{username}',
            'hash', bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
            'admin', admin
        )

    return text('Added user {0}'.format(username), status=201)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
