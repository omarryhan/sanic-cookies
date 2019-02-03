<p align="center">
    <a href="https://travis-ci.org/omarryhan/sanic-cookies"><img alt="Build Status" src="https://travis-ci.org/omarryhan/sanic-cookies.svg?branch=master"></a>
    <a href="https://github.com/omarryhan/sanic-cookies"><img alt="Software License" src="https://img.shields.io/badge/license-GNU-brightgreen.svg?style=flat-square"></a>
</p>

# Sanic Cookies

Code here is mostly borrowed from [sanic_session](https://github.com/xen/sanic_session).

I wanted to make some changes that would break a big part of `sanic_session`'s API, so I decided to create this repo instead.

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

### If enough people are interested, I can write some docs. Meanwhile, if you excuse me...

![Gotta go fast!!](http://sd.keepcalm-o-matic.co.uk/i/gotta-go-fast-sanic-fast.png)