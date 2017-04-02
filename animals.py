from sanic import Sanic
from sanic.response import text

from asyncio import sleep, Lock
import aioredis


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
        finally:
            self._lock.release()

        return self._redis


app = Sanic(__name__)

rp = RedisPoolSingleton()


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
    try:
        with await pool as redis:
            val = await redis.connection.execute('get', animal)
    except Exception as e:
        print(e)
        return text('The animal {0} was not found.'.format(animal), status=404)
    
    await sleep(5)
    return text(val.decode(), status=200)


@app.route('/animals/<animal>', methods=['PUT'])
async def add_animal(request, animal):
    """
    Add an animal to the database
    """
    pool = await rp.get_pool()
    with await pool as redis:
        redis.connection.execute('set', animal, request.body)

    return text('Added {0} to the farm'.format(animal), status=201)
    

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
