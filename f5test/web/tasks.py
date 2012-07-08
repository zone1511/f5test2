'''
Created on Jun 16, 2012

@author: jono
'''
from celery.task import task
import nose
import os
import logging
from f5test.noseplugins.testconfig import Signals

VENV = os.environ.get('VIRTUAL_ENV', '/home/jono/work/virtualenvs/f5test2')
LOG = logging.getLogger(__name__) 


@task
def add(x, y):
    logger = nosetests.get_logger()
    logger.info("TEST 123")
    return x + y

def _run(*arg, **kw):
    kw['exit'] = False
    return nose.core.TestProgram(*arg, **kw).success

@task
def nosetests(data):
    logger = nosetests.get_logger()
    logger.info("Started")
    logger.info("data: %s", data)
    
    # Must be fed valid data
    assert data
    assert data.get('project')
    assert data.get('build')
    
    def do_stuff(sender, config):
        params = config['stages']['main']['setup']['stage01-install-bigip-1']['parameters']
        params['version'] = data['project']
        params['build'] = data['build']
        nosetests.update_state(state='RUNNING', meta=config)

    args = ['', 
            '--verbose',
            '--verbosity=2',
            '--all-modules',
            '--nocapture',
            '--exe',
            '--console-redirect',
            '--tc=stages._enabled:1',
            '--with-progressive',
            '--tc-file=%s/config/suite_bvt_request.yaml' % VENV,
            '--log-config=%s/logging.conf' % VENV, 
    ]
    
    if data.get('debug'):
        args.append('--no-email')
        args.append('%s/tests/stirling-em/embvt/integration/filesystem/' % VENV)
    else:
        args.append('--attr=status=CONFIRMED,priority=1')
        args.append('--with-bvtinfo')
        args.append('--with-irack')
        args.append('%s/tests/stirling-em/embvt/' % VENV)
    
    # Connect the signal only during this iteration.
    with Signals.on_before_extend.connected_to(do_stuff):
        status = _run(argv=args)
    
    logging.shutdown()
    return status
