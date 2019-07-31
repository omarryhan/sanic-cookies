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

Sanic cookies supports both client side and server side cookies.

## Main deviations from sanic_session are

1. Interfaces are only responsible for reading/writing the `session_dict`. Session management logic is handled by the session object
2. No race conditions:

By using:

```python 3.7
async with request['session']:
    request['session']['foo'] = 'bar'
```

instead of:

```python 3.7
request['session']['foo'] = 'bar'
```

It is still however possible to use the `session_dict` without a context manager, but it will raise some warnings,
unless it's explicitly turned off (warn_lock=False)

3. A more simple implementation of SessionDict that helps me sleep in peace at night. (Probably less performant)
4. In memory interface schedules cleanup to avoid running out of memory
5. Encrypted client side cookies interface
6. Ability to add more than one interface to the same session
7. Authenticated Session implementation

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

## Usage

### Running multiple interfaces

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

### Running multiple sessions

```python 3.7
from sanic_cookies import Session, AuthSession, InMemory, InCookieEncrypted, AioRedis
from sanic import Sanic

inmem = InMemory()
aioredis = Aioredis(aioredis_pool_instance)
incookie = InCookieEncrypted(b'fernetsecretkey')

app = Sanic()

incookie_session = Session(
    app,
    master_interface=incookie,
    session_name='incookiesess',
    cookie_name='INCOOKIE'
)

generic_session = Session(
    app,
    master_interface=inmem,
    session_name='session',
    cookie_name='SESSION'
)

auth_session = AuthSession(
    app,
    master_interface=aioredis,
    session_name='auth_session',
    cookie_name='SECURE_SESSION'
)

# for production (HTTPs) set `secure=True` in your auth_session,
# but this will fail in local development

@app.route('/')
async def index(request):
    async with request['incookie_session'] as sess:
        sess['foo'] = 'bar'

    async with request['session'] as sess:
        sess['bar'] = 'baz'

    async with request['auth_session'] as sess:
        sess['baz'] = 'foo'
```

### AuthSession

Following up on the previous example:

```python 3.7
from sanic_cookies import login_required

@app.route('/login')
async def login(request):
    # 1. User verification logic

    # both will work (Whatever is json serializble will)
    # If you want to pickle an object simply change the default
    # encoder&decoder in the interfaces plugged in to your AuthSession
    authorized_user = 123 
    authorized_user = {'user_id': 123, 'email': 'foo@bar.baz'}

    # 2. Login user

    # Here we access the session object
    # (not the session dict that is accessible from the request) from the app
    await request.app.exts.auth_session.login_user(request, authorized_user)

    # 3. Use the session dict safely and exclusively for the logged in user

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

## Interfaces available

1. In memory

    ``` python 3.7
    from sanic_cookies import Session, InMemory
    from sanic import Sanic

    interface = InMemory()
    app = Sanic()
    Session(app, master_interface=interface)

    # You can skip this part if you don't want scheduled interface cleanup
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

3. Encrypted in-cookie (using the amazing cryptography.Fernet library)

    i. Open a Python terminal and generate a new Fernet key:

    ```python 3.7
    >>> from cryptography.fernet import Fernet

    >>> SESSION_KEY = Fernet.generate_key()

    >>> print(SESSION_KEY)

    b'copy me to your sanic app and keep me really secure'
    ```

    ii. Write your app

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

## Sessions available

1. Session (A generic session interface)
2. AuthSession (A session interface with login_user, logout_user, current_user logic)

## Other pluggable parts

1. Encoders and Decoders (Default to ujson)
2. SID factory (Default to uuid.uuid4)
3. Session dict implementation

## Contact 📧

I currently work as a freelance software devloper. Like my work and got a gig for me?

Want to hire me fulltime? Send me an email @ omarryhan@gmail.com

## Buy me a coffee ☕

**Bitcoin:** 3NmywNKr1Lzo8gyNXFUnzvboziACpEa31z

**Ethereum:** 0x1E1400C31Cd813685FE0f6D29E0F91c1Da4675aE

**Bitcoin Cash:** qqzn7rsav6hr3zqcp4829s48hvsvjat4zq7j42wkxd

**Litecoin:** MB5M3cE3jE4E8NwGCWoFjLvGqjDqPyyEJp

**Paypal:** https://paypal.me/omarryhan
