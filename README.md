<p align="center">
    <a href="https://travis-ci.org/omarryhan/sanic-cookies"><img alt="Build Status" src="https://travis-ci.org/omarryhan/sanic-cookies.svg?branch=master"></a>
    <a href="https://github.com/omarryhan/sanic-cookies"><img alt="Software License" src="https://img.shields.io/badge/license-GNU-brightgreen.svg?style=flat-square"></a>
</p>

# Sanic Cookies

Code here is mostly borrowed from [sanic_session](https://github.com/xen/sanic_session).

I wanted to make some changes that would break a big part of `sanic_session`'s API, so I decided to create this repo instead.

Sanic cookies supports both client side and server side cookies.

## Some of the main deviations from sanic_session are:

1. Interfaces are only responsible for reading/writing the `session_dict`. Session management logic is handled by the session object
2. No race conditions:

    By using:

        async with request['session']:
            request['session']['foo'] = 'bar'

    instead of:

        request['session']['foo'] = 'bar'

    It is still however possible to use the `session_dict` without a context manager, but it will raise some warnings,
    unless it's explicitly turned off (warn_lock=False)

3. A more simple implementation of SessionDict that helps me sleep in peace at night. (Probably less performant)
4. In memory interface schedules cleanup to avoid running out of memory
5. Encrypted client side cookies interface
6. Ability to add more than one interface to the same session
7. Authenticated Session implementation

## Quick Start

    from sanic_cookies import Session, InMemory

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

## Usage

### Running multiple interfaces

    from sanic_cookies import Session, InMemory, Aioredis

    inmem = InMemory()
    aioredis = AioRedis(aioredis_pool_instance)
    app = Sanic()
    sess = Session(app, master_interface=inmem, session_name='my_1st_sess')
    sess.add_interface(aioredis)

    @app.route('/')
    async def index(request):
        async with request['my_1st_session'] as sess:
            sess['foo'] = 'bar'
            # At this point 'foo' = 'bar' is written both to the inmemory interface and the aioredis interface

        async with request['my_1st_session'] as sess:
            assert sess['foo'] == 'bar'  # When reading, your session will always read from the "master_interface" in that case it's the inmem interface
        # Such pattern can be useful in many cases e.g. you want to share your session information with an analytics team

### Running multiple sessions

    from sanic_cookies import Session, AuthSession, InMemory, InCookieEnc, AioRedis

    inmem = InMemory()
    aioredis = Aioredis(aioredis_pool_instance)
    incookie = InCookieEnc(b'fernetsecretkey')

    app = Sanic()

    incookie_session = Session(app, master_interface=incookie, session_name='incookiesess', cookie_name='INCOOKIE')
    generic_session = Session(app, master_interface=inmem, session_name='session', cookie_name='SESSION')
    auth_session = AuthSession(app, master_interface=aioredis, session_name='auth_session', cookie_name='SECURE_SESSION', secure=True)

    @app.route('/')
    async def index(request):
        async with request['incookie_session'] as sess:
            sess['foo'] = 'bar'

        async with request['session'] as sess:
            sess['bar'] = 'baz'

        async with request['auth_session'] as sess:
            sess['baz'] = 'foo'

### AuthSession

Following up on the previous example:

    from sanic import response
    from sanic.exceptions import abort

    from sanic_cookies import login_required

    @app.route('/login')
    async def login(request):
        # 1. {{ User verification logic }}
        authorized_user = 123 
        authorized_user = {'user_id': 123, 'email': 'foo@bar.baz'}
        # both will work (Whatever is json serializble will)
        # If you want to pickle an object simply change the default encoder&decoder in the interfaces plugged in to your AuthSession

        # 2. Login user
        # Here we access the session object (not the session dict that is accessible from the request) from the app
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

## Interfaces available

1. In memory
2. Aioredis
3. Encrypted in-cookie (using the amazing cryptography.Fernet library)

## Sessions available

1. Session (A generic session interface)
2. AuthSession (A session interface with login_user, logout_user, current_user logic)

## Other pluggable parts

1. Encoders and Decoders (Default to ujson)
2. SID factory (Default to uuid.uuid4)
3. Session dict implementation

**If enough people are interested, I can write some docs. Meanwhile, if you excuse me...**

![Gotta go fast!!](http://sd.keepcalm-o-matic.co.uk/i/gotta-go-fast-sanic-fast.png)