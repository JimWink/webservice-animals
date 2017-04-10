import subprocess
from time import sleep

import pytest
import redis

@pytest.fixture(scope='module')
def server():
    with subprocess.Popen(['animals']) as server:
        sleep(3)
        yield
        server.kill()

@pytest.fixture
def preload():
    """
    Flush all items from the DB, but preserve the farmer if the
    server set it on startup. Add a few animals.
    """
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    farmer = r.hgetall('animals:user:farmer')
    r.flushdb()
    if farmer:
        r.hmset('animals:user:farmer', farmer)

    r.set('animals:item:cow', 'moo')
    r.set('animals:item:chicken', 'cluck')
    r.set('animals:item:pig', 'oink')    
