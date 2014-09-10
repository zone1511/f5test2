'''
Created on Aug 28, 2014

@author: jono
'''
from __future__ import absolute_import

import datetime
import logging
import time

from nose.case import Test
from nose.plugins.skip import SkipTest
import nose.util
import f5test.commands.icontrol as ICMD
from ...utils import Version
from ...interfaces.config import expand_devices

from . import ExtendedPlugin
from ...base import Options
from ...utils.net import get_local_ip
from ...utils.time import timesince


LOG = logging.getLogger(__name__)
PLUGIN_NAME = 'reporting'
A_HOST = 'f5.com'
INC_TEST_ATTRIBUTES = ('author', 'rank')
DEFAULT_DUTS = []


def test_address(test):
    """Return the result of nose's test_address(), None if it's stumped."""
    try:
        return nose.util.test_address(test)
    except TypeError:   # Explodes if the function passed to @with_setup applied
        pass            # to a test generator has an error.


def nose_selector(test):
    """Return the string you can pass to nose to run `test`, including argument
    values if the test was made by a test generator.

    Return "Unknown test" if it can't construct a decent path.

    """
    address = test_address(test)
    if address:
        _, module, rest = address

        if module:
            if rest:
                try:
                    return '%s:%s%s' % (module, rest, test.test.arg or '')
                except AttributeError:
                    return '%s:%s' % (module, rest)
            else:
                return module
    return 'Unknown test'


class Report(ExtendedPlugin):
    """
    Gather data about tests and store it in the "reporting" container.
    Enabled by default.
    """
    enabled = True
    score = 520

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        super(Report, self).configure(options, noseconfig)
        from ...interfaces.config import ConfigInterface
        from ...interfaces.testcase import ContextHelper

        self.cfgifc = ConfigInterface()
        self.context = ContextHelper()
        self.data = self.context.set_container(PLUGIN_NAME)
        self.duts = options.get('duts',
                                self.cfgifc.config.
                                get('plugins', {}).
                                get('_default_', {}).
                                get('duts', DEFAULT_DUTS))

#         cores = ContextHelper().set_container(CoreCollector.name)
#         if not cores.checked:
#             LOG.info('Information about cores will not be available in reports.')
#         self.data.cores = cores

    def set_runner_data(self):
        d = self.data
        d.result = Options(failures=[], errors=[], skipped=[], passed=[])
        d.nose_config = self.noseconfig
        d.config = self.cfgifc.open()
        d.test_runner_ip = get_local_ip(A_HOST)
        d.session = self.cfgifc.get_session()
        d.session_url = d.session.get_url(d.test_runner_ip)
        d.time = {}

    def set_duts_stats(self, devices):
        self.data.duts = []
        d = self.data.duts
        for device in devices:
            info = Options()
            info.device = device
            try:
                info.platform = ICMD.system.get_platform(device=device)
                info.version = ICMD.system.get_version(device=device)
                v = ICMD.system.parse_version_file(device=device)
                info.project = v.get('project')
                info.edition = v.get('edition', '')
            except Exception, e:
                LOG.error("%s: %s", type(e), e)
                info.version = Version()
                info.platform = ''
            if device.is_default():
                self.data.dut = info
            d.append(info)

    def prepareTestResult(self, result):
        self.data.test_result = result
        result.descriptions = 0
        result.getDescription = lambda y: nose_selector(y)  # @IgnorePep8

    def addFailure(self, test, err):
        result = self.data.result.failures
        result.append((test, err))

    def addError(self, test, err):
        if isinstance(test, Test):
            result = self.data.result.errors
            if err[0] is SkipTest:
                self.data.result.skipped.append((test, err))
            else:
                result.append((test, err))

    def addSuccess(self, test):
        result = self.data.result.passed
        result.append((test,))

    def startTest(self, test):
        """Initializes a timer before starting a test."""
        self.start = time.time()
        adr = nose_selector(test)
        test_meta = ["%s: %s" % (k, getattr(test.test, k, None))
                     for k in INC_TEST_ATTRIBUTES]
        LOG.debug('* Run * %s [%s]', adr, ", ".join(test_meta))

    def stopTest(self, test):
        """Initializes a timer before starting a test."""
        now = time.time()
        adr = nose_selector(test)
        LOG.debug('* Time * %s: %.3fs', adr, now - self.start)

    def begin(self):
        """Set the testrun start time.
        """
        self.set_runner_data()
        self.data.time.start = datetime.datetime.now()

    def finalize(self, result):
        """Set the testrun stop time and delta.
        """
        self.set_duts_stats(expand_devices(self.duts))
        d = self.data
        d.time.stop = datetime.datetime.now()
        d.time.delta = d.time.stop - d.time.start
        d.time.delta_str = timesince(d.time.start)
