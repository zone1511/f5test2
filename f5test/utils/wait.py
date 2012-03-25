'''
Created on Aug 10, 2011

@author: jono
'''
import sys
import time
import traceback
import logging

LOG = logging.getLogger(__name__) 

class WaitTimedOut(Exception):
    pass


def wait(function, condition=None, progress_cb=None, timeout=180, interval=5, stabilize=0,
         message=None):
    
    if not condition:
        condition = lambda x:x

    assert callable(function), "The command must be callable!"
    assert callable(condition), "The condition must be callable!"
    now = start = time.time()
    
    good = False
    last_ret = ret = None
    stable = 0
    while now - start < timeout:
        success = False
        try:
            ret = function()
            success = True
            if condition(ret):
                good = True
        except:
            err = sys.exc_info()
            tb = ''.join(traceback.format_exception(*err))
            LOG.debug('Error running command. (%s)', tb)
        finally:
            if good:
                LOG.debug('Criteria met (%s). Cleaning up...', ret)
                if stable >= stabilize:
                    break
                else:
                    if last_ret == ret:
                        LOG.debug('Criteria met and stable')
                        stable += interval
                    else:
                        LOG.debug('Criteria met but not stable')
                        stable = 0
                last_ret = ret
            else:
                stable = 0
                if success:
                    if progress_cb:
                        info = progress_cb(ret)
                        if info:
                            LOG.info(info)
                    else:
                        LOG.debug('Criteria not met (%s). Sleeping %ds...', ret, 
                                  interval)
            time.sleep(interval)
            now = time.time()
    else:
        LOG.warn('Criteria not met. Giving up...')
        if message:
            raise WaitTimedOut(message)
        raise WaitTimedOut('Condition not met after %d seconds.' % 
                              timeout)
    return ret
