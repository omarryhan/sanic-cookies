<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/7/70/Cookie.png" alt="Logo" width="250" height="250"/>
  <p align="center">
    <a href="https://github.com/omarryhan/sanic-cookies"><img alt="Software License" src="https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat-square" /></a>
    <a href="https://travis-ci.org/omarryhan/sanic-cookies"><img alt="Build Status" src="https://travis-ci.org/omarryhan/sanic-cookies.svg?branch=master" /></a>
    <a href="https://github.com/python/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg" /></a>
    <a href="https://pepy.tech/badge/sanic-cookies"><img alt="Downloads" src="https://pepy.tech/badge/sanic-cookies" /></a>
    <a href="https://pepy.tech/badge/sanic-cookies/month"><img alt="Monthly Downloads" src="https://pepy.tech/badge/sanic-cookies/month" /></a>
  </p>
</p>

# Sanic Cookies

Much of the code here is borrowed from [sanic_session](https://github.com/xen/sanic_session).

I wanted to make some changes that would break a big part of `sanic_session`'s API, so I decided to create this repo instead.

Sanic Cookies emphasizes on:

1. Security

2. API stability

## Main differences from [sanic_session](https://github.com/xen/sanic_session) are:

- Authenticated Session implementation (Session object with login and logout logic)

- No race conditions:

  *By using:*

    ```python 3.7
    async with request['session']:
        request['session']['foo'] = 'bar'
    ```

  *instead of:*

    ```python 3.7
    request['session']['foo'] = 'bar'
    ```

  It is still however possible to use the `session_dict` without a context manager, but it will raise some warnings,
  unless it's explicitly turned off (warn_lock=False)

  **Note:**

    The locking mechanism used here only keeps track of locks on a thread-level, which means, an application that is horizontally scaled or one that runs on more than one process won't fully benefit from the locking mechanism that sanic-cookies currently has in place and might encounter some race conditions.
    I have plans to introduce a distributed locking mechanism. Probably using something like: [Aioredlock](https://github.com/joanvila/aioredlock).
    But for now, you should know that the locking mechanism that is currently in place will not work in a multi-process environment.

- Encrypted client side cookie interface

- AsyncPG interface

## Minor differences:

- Ability to add more than one interface to the same session

- A simpler implementation of SessionDict that helps me sleep in peace at night

- In memory interface schedules cleanup to avoid running out of memory

- Interfaces are only responsible for reading/writing the `SessionDict`:

- Session management logic is handled by the `Session` object

## Setup ⚙️

```bash
$ pip install sanic_cookies
```

## Quick Start

```python 3.7
from sanic_cookies import Session, InMemory
from sanic import Sanic

app = Sanic()
Session(app, master_interface=InMemory())

@app.route('/')
async def handler(request):
    async with request['session'] as sess:
        sess['foo'] = 'bar'
```

## Interfaces (storage) available:

- In-memory (Not recommended for production)
- Aioredis 
- Encrypted in-cookie (using the amazing cryptography.Fernet library)
- Gino-AsyncPG (Postgres 9.5+):

## Sessions available

1. Session (A generic session interface)
2. AuthSession (A session interface with login_user, logout_user, current_user logic)


## AuthSession

An Auth session is just a normal session but with user authentication capabilities

```python 3.7
from sanic_cookies import AuthSession, AioRedis, login_required
from sanic import Sanic

aioredis = Aioredis(aioredis_pool_instance)

app = Sanic()

auth_session = AuthSession(
    app,
    master_interface=aioredis,
    session_name='auth_session',
    cookie_name='SECURE_SESSION'
)

@app.route('/login')
async def login(request):
    # both will work (Whatever is JSON serializble will)
    authorized_user = 123 
    authorized_user = {'user_id': 123, 'email': 'foo@bar.baz'}

    # Here we access the session object
    # (not the session dict that is accessible from the request) from the app
    await request.app.exts.auth_session.login_user(request, authorized_user)

    # Now you can use the session dict safely and exclusively for the logged in user
    async with request['auth_session'] as sess:
        sess['foo'] = 'bar'
        current_user = sess['current_user']
    assert current_user == await request.app.exts.auth_session.current_user()

@app.route('/logout')
async def logout(request):
    async with request['auth_session'] as sess:
        assert sess['foo'] == 'bar'  # From before

    await request.app.exts.auth_session.logout_user(request)  # Resets the session

    async with request['auth_session'] as sess:
        assert sess.get('foo') is None  # should never fail
        assert sess.get('current_user') is None  # should never fail

@app.route('/protected')
@login_required()
async def protected(request):
    assert await request.app.exts.auth_session.current_user() is not None  # should never fail
```

## Interface Setup

1. In memory

    ``` python 3.7
    from sanic_cookies import Session, InMemory
    from sanic import Sanic

    interface = InMemory()
    app = Sanic()
    Session(app, master_interface=interface)

    # You can skip this part if you don't want scheduled stale sessions cleanup
    @app.listener('before_server_start')
    def init_inmemory(app, loop):
        interface.init()
    @app.listener('after_server_stop')
    def kill_inmemory(app, loop):
        interface.kill()

    @app.route('/')
    async def handler(request):
        async with request['session'] as sess:
            sess['foo'] = 'bar'
    ```

2. Aioredis

    ```python 3.7
    from aioredis import Aioredis
    from sanic_cookies import Aioredis as AioredisInterface
    from sanic import Sanic

    app = Sanic()
    aioredis_pool_instance = Aioredis()
    aioredis = AioredisInterface(aioredis_pool_instance)
    Session(app, master_interface=interface)

    @app.route('/')
    async def handler(request):
        async with request['session'] as sess:
            sess['foo'] = 'bar'
    ```

3. Encrypted in-cookie

    i. Open a Python terminal and generate a new Fernet key:

    ```python 3.7
    >>> from cryptography.fernet import Fernet

    >>> SESSION_KEY = Fernet.generate_key()

    >>> print(SESSION_KEY)

    b'copy me to your sanic app and keep me really secure'
    ```

    ii. Your app

    ```python 3.7
    from sanic import Sanic
    from sanic_cookies import Session, InCookieEncrypted

    app = Sanic()
    app.config.SESSION_KEY = SESSION_KEY

    Session(
        app,
        master_interface=InCookieEncrypted(app.config.SESSION_KEY),
    )

    @app.route('/')
    async def handler(request):
        async with request['session'] as sess:
            sess['foo'] = 'bar'
    ```

4. Gino-AsyncPG (Postgres 9.5+):

    i. Manually create a table:

    ```sql
    CREATE TABLE IF NOT EXISTS sessions
    (
        created_at timestamp without time zone NOT NULL,
        expires_at timestamp without time zone,
        sid character varying,
        val character varying,
        CONSTRAINT sessions_pkey PRIMARY KEY (sid)
    );
    ```

    ii. Add the interface:

    ```python 3.7
    from sanic import Sanic
    from gino.ext.sanic import Gino
    from sanic_cookies import GinoAsyncPG

    from something_secure import DB_SETTINGS

    app = Sanic()
    app.config.update(DB_SETTINGS)
    db = Gino()
    db.init_app(app)

    interface = GinoAsyncPG(client=db)
    auth_session = AuthSession(app, master_interface=interface)

    if __name__ == '__main__':
        app.run(host='127.0.0.1', port='8080')
    ```

## Master interface & multiple interfaces

A master interface is the interface that sanic-cookies will read from. The word master is relevant for when you have multiple interfaces. When you have multiple interfaces, sanic-cookies will only read from the master-interface but write to all interfaces.

```python 3.7
from sanic_cookies import Session, Aioredis
from sanic import Sanic

aioredis = AioRedis(aioredis_pool_instance)
app = Sanic()
sess = Session(app, master_interface=aioredis, session_name='my_1st_sess')

@app.route('/')
async def index(request):
    async with request['my_1st_session'] as sess:
        sess['foo'] = 'bar'

    async with request['my_1st_session'] as sess:
        # When reading, your session will always read from the "master_interface"
        assert sess['foo'] == 'bar'
```

Running multiple interfaces (transports):

```python 3.7
from sanic_cookies import Session, InMemory, Aioredis
from sanic import Sanic

inmem = InMemory()
aioredis = AioRedis(aioredis_pool_instance)
app = Sanic()
sess = Session(app, master_interface=inmem, session_name='my_1st_sess')
sess.add_interface(aioredis)

@app.route('/')
async def index(request):
    async with request['my_1st_session'] as sess:
        sess['foo'] = 'bar'
        # At this point 'foo' = 'bar' is written both to the inmemory
        # interface and the aioredis interface

    async with request['my_1st_session'] as sess:
        # When reading, your session will always read from the "master_interface"
        # In that case it's the inmem interface
        assert sess['foo'] == 'bar'
    # Such pattern can be useful in many cases 
    # e.g. you want to share your session information with an analytics team
```
