'''
Created on Jul 21, 2013
Source: http://theorangeduck.com/page/synchronized-python

@author: jono
'''
import thread
import threading
import types
from functools import wraps
import logging
from .wait import wait_args

LOG = logging.getLogger(__name__)


def synchronized_with_attr(lock_name):

    def decorator(method):

        def synced_method(self, *args, **kws):
            lock = getattr(self, lock_name)
            with lock:
                return method(self, *args, **kws)

        return synced_method

    return decorator


def synchronized_with(lock):

    def synchronized_obj(obj):

        if type(obj) is types.FunctionType:

            obj.__lock__ = lock

            def func(*args, **kws):
                with lock:
                    return obj(*args, **kws)
            return func

        elif type(obj) is types.ClassType:
            orig_init = obj.__init__

            def __init__(self, *args, **kws):
                self.__lock__ = lock
                orig_init(self, *args, **kws)
            obj.__init__ = __init__

            for key in obj.__dict__:
                val = obj.__dict__[key]
                if type(val) is types.FunctionType:
                    decorator = synchronized_with(lock)
                    obj.__dict__[key] = decorator(val)

            return obj

    return synchronized_obj


def synchronized(item):

    if type(item) is types.StringType:
        decorator = synchronized_with_attr(item)
        return decorator(item)

    if type(item) is thread.LockType:
        decorator = synchronized_with(item)
        return decorator(item)

    else:
        new_lock = threading.Lock()
        decorator = synchronized_with(new_lock)
        return decorator(item)


def repeat(times):
    def _my_decorator(f):
        def test_wrapper(*args, **kwargs):
            for i in range(0, times):
                LOG.info('* Iteration %d *', i + 1)
                f(*args, **kwargs)
        return wraps(f)(test_wrapper)
    return _my_decorator


def retry(timeout=180, interval=5, negated=False):
    def _my_decorator(f):
        def test_wrapper(*args, **kwargs):
            def f2():
                f(*args, **kwargs)
                return True
            wait_args(f2, timeout=timeout, interval=interval, negated=negated,
                      progress_message='* Test case failed. Retrying...',
                      timeout_message='Test failed failed consistently for {0} seconds. Check logs for full traceback(s).')
        return wraps(f)(test_wrapper)
    return _my_decorator


if __name__ == '__main__':
    @repeat(2)
    def f():
        print 'a'
    f()
