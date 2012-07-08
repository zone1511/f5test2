'''
Created on Aug 10, 2011

@author: jono
'''
from __future__ import absolute_import
import sys
import time
import traceback
import logging

LOG = logging.getLogger(__name__) 

class WaitTimedOut(Exception):
    pass


class Wait(object):
    timeout_message = "Criteria not met after {0} seconds."
    progress_message = None
    
    def __init__(self, timeout=180, interval=5, stabilize=0, negated=False, 
                 timeout_message=None, progress_message=None):
        self.timeout = timeout
        self.interval = interval
        self.stabilize = stabilize
        self.negated = negated
        
        if timeout_message:
            self.timeout_message = timeout_message
        
        if progress_message:
            self.progress_message = progress_message

    def function(self, *args, **kwargs):
        return True

    def run(self, *args, **kwargs):
        last_success = result = None
        stable = 0
        end = time.time() + self.timeout
        
        while time.time() < end:
            success = False
            try:
                result = self.function(*args, **kwargs)
                success = self.test_result(result)
                self.progress(result)
                #if not success:
                #    LOG.warning('Unexpected result: %s', result)
            except:
                err = sys.exc_info()
                tb = ''.join(traceback.format_exception(*err))
                success = self.test_error(*err)
                LOG.debug("Exception occured during wait():\n%s", tb)
                #if not success:
                #    LOG.warning('Unexpected error: %s', tb)
            finally:
                self.cleanup()
                if success:
                    self.criteria_met(result)
                else:
                    stable = 0
                    self.criteria_not_met(result)
                
                if success:
                    if stable >= self.stabilize:
                        break
                    else:
                        if stable == 0 or last_success == success:
                            self.criteria_met_stable(result)
                            stable += self.interval
                        else:
                            self.criteria_met_not_stable(result)
                            stable = 0
                
                last_success = success
                time.sleep(self.interval)
        else:
            self.fail(result)
            raise WaitTimedOut(self.timeout_message.format(self.timeout))
        
        return result
    
    def test_result(self, result):
        return bool(result) ^ self.negated

    def test_error(self, exc_type, exc_value, exc_traceback):
        return False ^ self.negated
    
    def criteria_met(self, result):
        LOG.debug('Criteria met.')

    def criteria_not_met(self, result):
        LOG.debug('Criteria not met.')

    def fail(self, result):
        LOG.warn('Giving up...')

    def criteria_met_stable(self, result):
        LOG.debug('Criteria met and stable.')
    
    def criteria_met_not_stable(self, result):
        LOG.debug('Criteria met but not stable. Timer reset.')

    def progress(self, result):
        if self.progress_message:
            LOG.info(self.progress_message.format(result))

    def cleanup(self):
        pass


class CallableWait(Wait):

    def __init__(self, func, condition=None, progress_cb=None, *args, **kwargs):
        self._func = func
        self._condition = condition
        self._progress_cb = progress_cb
        super(CallableWait, self).__init__(*args, **kwargs)

    def function(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def test_result(self, result):
        if self._condition:
            return self._condition(result)
        return super(CallableWait, self).test_result(result)

    def progress(self, result):
        if self._progress_cb:
            ret = self._progress_cb(result)
            LOG.info(ret)
        else:
            super(CallableWait, self).progress(result)

def wait_args(func, func_args=None, func_kwargs=None, *args, **kwargs):
    if not func_args:
        func_args = []
    if not func_kwargs:
        func_kwargs = {}

    return CallableWait(func, *args, **kwargs).run(*func_args, **func_kwargs)

def wait(func, condition=None, progress_cb=None, *args, **kwargs):
    return CallableWait(func, condition, progress_cb, *args, **kwargs).run()


if __name__ == '__main__':
    logging.basicConfig(level=0)

    Wait(interval=0.5, timeout=3, stabilize=1, function=lambda: True).run()
