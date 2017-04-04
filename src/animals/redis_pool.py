"""
Wrapper coroutines to handle pool of redis connections
"""
import aioredis


pool = None


async def setup_redis_pool(config, sslctx=None):
    """
    Create the redis pool singleton

    :param dict config: configuration options for the connection
    :param ssl.SSLContext|None sslctx: SSL Context object for secure
        connections.
    """
    global pool
    pool = await aioredis.create_pool(
        (config.get('host', 'localhost'), config.get('port', 6379)),
        minsize=int(config.get('minsize', 1)),
        maxsize=int(config.get('maxsize', 10)),
        password=config.get('password', None),
        ssl=sslctx
    )


async def shutdown_redis_pool():
    """
    Close the redis connection pool
    """
    pool.close()
    await pool.wait_closed()


async def pool_execute(command, *args, **kwargs):
    """
    Execute redis command in a pool connection

    :param str command: redis command

    :returns: Result of redis command
    """
    async with pool.get() as redis:
        result = await redis.connection.execute(command, *args, **kwargs)
    return result
