
from asyncio import sleep
from base64 import b64decode
import ssl

import bcrypt
from sanic import Blueprint
from sanic.response import text

from animals.auth import requires_auth, requires_admin
from animals.redis_pool import setup_redis_pool, shutdown_redis_pool
from animals.redis_pool import pool_execute as execute


bp = Blueprint('animals_blueprint')


@bp.listener('before_server_start')
async def setup_server(app, loop):
    redis_conf = app.config.get('redis', {})
    sslctx = None
    if redis_conf.get('use_ssl', False):
        sslctx = ssl.SSLContext()
        sslctx.load_cert_chain(redis_conf['ssl_cert'])

    await setup_redis_pool(redis_conf, sslctx=sslctx)

    farmer_conf = app.config.get('farmer', {})
    password = farmer_conf.get('password', '12345')
    await execute(
        'hmset',
        'animals:user:farmer',
        'hash', bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
        'admin', 'true'
    )


@bp.listener('after_server_stop')
async def shutdown_server(app, loop):
    await shutdown_redis_pool()


@bp.route('/')
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
    val = await execute('get', f'animals:item:{animal}')
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
    await execute('set', f'animals:item:{animal}', request.body)

    return text('Added {0} to the farm'.format(animal), status=201)


@bp.route('/users/<username>', methods=['POST'])
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
    await execute(
        'hmset',
        f'animals:user:{username}',
        'hash', bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
        'admin', admin
    )

    return text('Added user {0}'.format(username), status=201)
