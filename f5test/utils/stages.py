'''
Created on Feb 9, 2012

@author: jono
'''
from __future__ import absolute_import
from f5test.interfaces.config import (expand_devices, ConfigInterface)
from f5test.macros.base import Macro, MacroThread
from f5test.utils.stage.base import Stage, StageError
from nose.config import _bool
import inspect
import os

from f5test.base import Options
from Queue import Queue
import traceback
import logging

from f5test.utils.stage.install import InstallSoftwareStage  # @UnusedImport
from f5test.utils.stage.em import EMDiscocveryStage, EMInstallSoftwareStage  # @UnusedImport
from f5test.utils.stage.ha import HAStage  # @UnusedImport
from f5test.utils.stage.config import ConfigStage, KeySwapStage, SetPasswordStage  # @UnusedImport
from f5test.utils.stage.misc import TweaksStage  # @UnusedImport
from f5test.utils.stage.check import ScaleCheckStage  # @UnusedImport
from f5test.utils.stage.ha_bigiq import HABigiqStage  # @UnusedImport

__all__ = ['InstallSoftwareStage', 'EMDiscocveryStage', 'EMInstallSoftwareStage',
           'HAStage', 'ConfigStage', 'KeySwapStage', 'SetPasswordStage',
           'TweaksStage', 'SanityCheck', 'ScaleCheckStage', 'HABigiqStage']

LOG = logging.getLogger(__name__)
DEFAULT_PRIORITY = 100
DEFAULT_TIMEOUT = 600
DEFAULT_DISCOVERY_DELAY = 30
ENABLE_KEY = 'enabled'
PRIORITY_KEY = 'priority'
GROUP_KEY = 'group'
TYPE_KEY = 'type'
PARAMETERS_KEY = 'parameters'
QUICK_KEY = '_quick'
MAX_THREADS = 10


def carry_flag(d, flag=None):
    """
    Given the dict:
    key1:
        _enabled: 1
        subkey1:
            key: val
        subkey2:
            key: val

    The resulting dict after running carry_flag() on it will be:
    key1:
        _enabled: 1
        subkey1:
            _enabled: 1
            key: val
        subkey2:
            _enabled: 1
            key: val
    """
    if flag != None:
        if TYPE_KEY in d:
            d.setdefault(ENABLE_KEY, flag)
    else:
        flag = d.get(ENABLE_KEY)

    for v in d.itervalues():
        if isinstance(v, dict):
            carry_flag(v, flag)


def process_stages(stages, section, context, stop_on_error=True):
    if not stages:
        LOG.debug('No stages found.')
        return

    # Replicate the "_enabled" flag.
    carry_flag(stages)

    # Build the stage map with *ALL* defined stage classes in this file.
    stages_map = {}
    for value in globals().values():
        if inspect.isclass(value) and issubclass(value, Stage) and value != Stage:
            stages_map[value.name] = value

    # Focus only on our stages section
    for key in section.split('.'):
        stages = stages.get(key, Options())

    # Sort stages by priority attribute and stage name.
    stages = sorted(stages.iteritems(), key=lambda x: (isinstance(x[1], dict) and
                                                      x[1].get(PRIORITY_KEY,
                                                               DEFAULT_PRIORITY),
                                                      x[0]))

    config = ConfigInterface().config
    # Group stages of the same type. The we spin up one thread per stage in a
    # group and wait for threads within a group to finish.
    sg_dict = {}
    sg_list = []
    for name, specs in stages:
        if not specs or name.startswith('_'):
            continue
        assert TYPE_KEY in specs, "%s stage is invalid. No type specified." % name

        specs = Options(specs)
        key = specs.get(GROUP_KEY, "{0}-{1}".format(name, specs[TYPE_KEY]))

        group = sg_dict.get(key)
        if not group:
            sg_dict[key] = []
            sg_list.append(sg_dict[key])
        sg_dict[key].append((name, specs))

    LOG.debug("sg_list: %s", sg_list)
    for stages in sg_list:
        q = Queue()
        pool = []
        for stage in stages:
            description, specs = stage
            if not specs or not _bool(specs.get(ENABLE_KEY)):
                continue

            LOG.info("Processing stage: %s", description)
            # items() reverts <Options> to a simple <dict>
            specs = Options(specs)
            if not stages_map.get(specs[TYPE_KEY]):
                LOG.warning("Stage '%s' (%s) not defined.", description, specs[TYPE_KEY])
                continue

            stage_class = stages_map[specs[TYPE_KEY]]
            parameters = specs.get(PARAMETERS_KEY) or Options()
            parameters._context = context

            devices = expand_devices(specs)
            if devices is None:
                stage_class(parameters).run()
            elif devices == []:
                LOG.error("Stage %s requires devices but found none" % description)
            else:
                if not devices:
                    LOG.warning('No devices found for stage %s', description)
                for device in devices:
                    stage = stage_class(device, parameters)
                    name = '%s :: %s' % (description, device.alias) if device else description
                    t = MacroThread(stage, q, name=name, config=config)
                    t.start()
                    pool.append(t)
                    if not stage_class.parallelizable or not specs.get('parallelizable', True):
                        t.join()

                    # Cap the number parallel threads
                    if len(pool) >= specs.get('threads', MAX_THREADS):
                        map(lambda x: x.join(), pool)
                        pool[:] = []

        LOG.debug('Waiting for threads...')
        for t in pool:
            t.join()

        if not q.empty():
            stages = []
            while not q.empty():
                ret = q.get(block=False)
                thread, exc_info = ret.popitem()
                stages.append((thread, exc_info))
                LOG.error('Exception while "%s"', thread.getName())
                for line in traceback.format_exception(*exc_info):
                    LOG.error(line.strip())

            if stop_on_error:
                raise StageError(stages)


class SanityCheck(Macro):
    """
    Do some sanity checks before running any other stages:

    - Check that 'root ca', 'build' and 'logs' paths are defined;
    - Chack that <build>/bigip directory exists;
    - Check that <root ca> directory is writable;
    - Verify that <logs> directory is writable;
    - Make sure <logs> directory has more than 100MB free.
    """

    def run(self):
        configifc = ConfigInterface()
        config = configifc.open()

        if not config.paths:
            LOG.info('Test runner sanity skipped.')
            return

        assert config.paths.build, 'CM Build path is not set in the config'
        assert config.paths.logs, 'Logs path is not set in the config'

        sample = os.path.join(config.paths.build, 'bigip')
        if not os.path.exists(sample):
            raise StageError("%s does not exist" % sample)

        sample = config.paths.get('logs')
        sample = os.path.expanduser(sample)
        sample = os.path.expandvars(sample)
        if not os.access(sample, os.W_OK):
            raise StageError("Logs dir: %s is not writable" % sample)

        stats = os.statvfs(sample)
        if not (stats.f_bsize * stats.f_bavail) / 1024 ** 2 > 100:
            raise StageError("Logs dir: %s has not enough space left" % sample)

        LOG.info('Test runner sanity check passed!')
