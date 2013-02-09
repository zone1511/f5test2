'''
Created on Jun 16, 2012

@author: jono
'''
from celery import task
import nose
import os
import logging
import re
from f5test.noseplugins.testconfig import Signals, EXTENDS_KEYWORD
from billiard import current_process

BVTINFO_PROJECT_PATTERN = '(\D+)?(\d+\.\d+\.\d+)-?(hf\d+)?'
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


def get_harness_config(logger, harnesses):
    i = current_process().index
    try:
        return harnesses[i]
    except IndexError:
        logger.warn("Worker %d doesn't have a harness associated. Add one in "
                    "HARNESSES or reduce the CELERY_CONCURRENCY", i)


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
        config['bvtinfo'] = {}
        config['bvtinfo']['project'] = data['project']
        config['bvtinfo']['build'] = data['build']
        match = re.match(BVTINFO_PROJECT_PATTERN, data['project'])
        if match:
            params['version'] = match.group(2)
            if match.group(3):
                params['hotfix'] = match.group(3)
        else:
            params['version'] = data['project']
        params['build'] = data['build']

        harness = get_harness_config(logger, config['web']['harnesses'])
        if not harness:
            return
        config[EXTENDS_KEYWORD].append(harness)
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
        args.append('%s/tests/solar/bvt/integration/filesystem/' % VENV)
    else:
        args.append('--attr=status=CONFIRMED,priority=1')
        args.append('--with-bvtinfo')
        args.append('--with-irack')
        args.append('%s/tests/solar/bvt/' % VENV)

    # Connect the signal only during this iteration.
    with Signals.on_before_extend.connected_to(do_stuff):
        status = _run(argv=args)

    logging.shutdown()
    return status
