'''
Created on Jun 16, 2012

@author: jono
'''
import celery
from celery.result import AsyncResult
from celery.signals import setup_logging  # ,after_setup_task_logger
from celery.utils.log import get_task_logger
from f5test.interfaces.config.driver import Signals
from f5test.base import AttrDict
from f5test.utils.dicts import merge
from f5test.macros.install import InstallSoftware
from f5test.macros.tmosconf import ConfigPlacer
from f5test.macros.ictester import Ictester
import inspect
import logging.config
from logging.handlers import BufferingHandler
import nose
import os
import sys
import time
import collections

logging.raiseExceptions = 0

LOG = get_task_logger(__name__)
VENV = os.environ.get('VIRTUAL_ENV', '../../../')
TESTS_DIR = os.path.join(VENV, 'tests')
# if VENV is None:
#    raise RuntimeError("You must first activate the virtualenv (e.g. workon my_environment).")
LOG_CONFIG = 'logging.conf'
MEMCACHED_META_PREFIX = 'f5test-task-'
# URL_REGEX = r'(\(?\bhttp://[-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_()|])'
MAX_LOG_LINE = 1024


# Setup logging only once when celery is initialized.
# Never use --log-config with nosetests when running under celery!
def _setup_logging(**kw):
    logging.config.fileConfig(os.path.join(VENV, LOG_CONFIG))
# after_setup_task_logger.connect(_setup_logging)
setup_logging.connect(_setup_logging)


# This unloads all our modules, thus forcing nose to reload all tests.
def _clean_sys_modules(tests_path=TESTS_DIR):
    for name, module in sys.modules.items():
        if (module and inspect.ismodule(module) and hasattr(module, '__file__')) \
                and module.__file__.startswith(tests_path):
            del sys.modules[name]


class MyMemoryHandler(BufferingHandler):

    def __init__(self, task, level, *args, **kwargs):
        super(MyMemoryHandler, self).__init__(*args, **kwargs)
        self.task = task
        self.level = level
        self.tip = 0
        self.buffer = collections.deque([], maxlen=MAX_LOG_LINE)

    def emit(self, record):
        item = AttrDict()
        item.name = record.name
        item.levelname = record.levelname
        item.message = record.message[:MAX_LOG_LINE]
        # item.message = re.sub(URL_REGEX, r'<a href="\1">\1</a>', record.message)
        item.timestamp = time.strftime('%b %d %H:%M:%S',
                                       time.localtime(record.created))
        # for x in item:
        #    if x not in ('levelname', 'asctime', 'message'):
        #        item.pop(x)
        self.buffer.append(item)
        self.tip += 1
        self.task.save_meta(logs=list(self.buffer), tip=self.tip)
        # self.task.update_state(state='PENDING', meta=self.task._result)


class MyAsyncResult(AsyncResult):

    def load_meta(self):
        return self.backend.get(MEMCACHED_META_PREFIX + self.id)


class DebugTask(celery.Task):
    abstract = True
    _meta = AttrDict()

    def AsyncResult(self, task_id):
        """Get AsyncResult instance for this kind of task.

        :param task_id: Task id to get result for.

        """
        return MyAsyncResult(task_id, backend=self.backend,
                             task_name=self.name)

    def clear_meta(self):
        self._meta.clear()

    def save_meta(self, **kwargs):
        self._meta.update(**kwargs)
        self.backend.set(MEMCACHED_META_PREFIX + self._id, self._meta)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if self.request.is_eager:
            self.backend.mark_as_failure(task_id, exc, einfo.traceback)

    def on_success(self, retval, task_id, args, kwargs):
        if self.request.is_eager:
            self.backend.mark_as_done(task_id, retval)

    def __call__(self, *args, **kwargs):
        self._id = self.request.id

        if not self.request.is_eager:
            self.update_state(state=celery.states.STARTED)
            # LOG.setLevel(level)

        if self.request.is_eager:
            logging.basicConfig(level=logging.INFO)

        self.clear_meta()
        handler = MyMemoryHandler(task=self, level=logging.INFO, capacity=2000)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            return super(DebugTask, self).__call__(*args, **kwargs)
        finally:
            root_logger.removeHandler(handler)


@celery.task(base=DebugTask)
def add(x, y, user_input=None):
    add.save_meta(user_input=user_input)
    for i in range(10):
        time.sleep(1)
        LOG.info("Munching %d", i)
        LOG.warn("Warning!! %d", i)

    LOG.error("I just died! Nah, I'm kidding.")
    if x == y:
        raise ValueError("x and y must be different!")

    return int(x) + int(y)


def _run(*arg, **kw):
    kw['exit'] = False
#    try:
    return nose.core.TestProgram(*arg, **kw).success
#    except:
#        LOG.error('Nose crashed:')
#        err = sys.exc_info()
#        LOG.error(''.join(traceback.format_exception(*err)))
#        raise


@celery.task(base=DebugTask)
def nosetests(data, args, user_input=None):
    _clean_sys_modules()
    nosetests.save_meta(user_input=user_input)
#    LOG.info("Started")
#    LOG.info("data: %s", data)

    def merge_config(sender, config):
        merge(config, data)
        v = config.plugins.email.variables
        v.task_id = nosetests._id
        v.referer = "%s#%s" % (user_input._referer, nosetests._id)

    for i, arg in enumerate(args):
        args[i] = arg.format(VENV=VENV)

    # Connect the signal only during this iteration.
    with Signals.on_after_extend.connected_to(merge_config):
        status = _run(argv=args)

    logging.shutdown()
    # XXX: nose logger leaks handlers. See nose/config.py:362
    logging.getLogger('nose').handlers[:] = []

    return status


@celery.task(base=DebugTask)
def confgen(address, options, user_input=None):
    confgen.save_meta(user_input=user_input)
    return ConfigPlacer(options, address=address).run()


@celery.task(base=DebugTask)
def install(address, options, user_input=None):
    install.save_meta(user_input=user_input)
    return InstallSoftware(options, address=address).run()


@celery.task(base=DebugTask)
def ictester(address, method, options, params, user_input=None):
    ictester.save_meta(user_input=user_input)
    return Ictester(options, method, address=address, params=params).run()
