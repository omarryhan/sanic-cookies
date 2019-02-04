import time

from sanic_cookies.interfaces.inmemory import ExpiringDict

def test_entry_expires():
    K = 'foo'
    V = 'BAR'
    TIME = 0.1

    expiring_dict = ExpiringDict()

    expiring_dict.set(K, TIME, V)
    assert expiring_dict.get(K) == V
    assert len(expiring_dict) == 1
    assert len(expiring_dict.expiry_times) == 1
    time.sleep(TIME)
    assert expiring_dict.get(K) is None
    assert len(expiring_dict) == 0
    assert len(expiring_dict.expiry_times) == 0

def test_cleanup():
    # TODO
    pass