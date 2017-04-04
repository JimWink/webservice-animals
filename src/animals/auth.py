"""
Authentication and authorization helpers
"""
from base64 import b64decode
from functools import wraps

import bcrypt
from sanic.response import text

from animals.redis_pool import pool_execute as execute


async def check_auth(username, password):
    hashed = await execute('hget', f'animals:user:{username}', 'hash')
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
    admin = await execute('hget', f'animals:user:{username}', 'admin')
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
