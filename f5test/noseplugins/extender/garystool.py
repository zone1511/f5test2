'''
Created on Aug 28, 2014

@author: jono
'''
import inspect
import json
import logging
import os
import traceback
import unittest
from itertools import chain

from ...base import Options
from . import ExtendedPlugin, PLUGIN_NAME

LOG = logging.getLogger(__name__)
DEFAULT_FILENAME = 'results.json'


class GarysTool(ExtendedPlugin):
    """
    Generate a json report.
    """
    enabled = True

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--with-garystool', action='store_true',
                          dest='with_garystool', default=False,
                          help="Enable Gary's tool reporting. (default: no)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        from ...interfaces.testcase import ContextHelper
        super(GarysTool, self).configure(options, noseconfig)
        self.filename = options.get('filename', DEFAULT_FILENAME)
        self.data = ContextHelper().set_container(PLUGIN_NAME)
        self.enabled = noseconfig.options.with_garystool

    def report_results(self):
        LOG.info("Reporting results for Gary's tool...")

    def dump_json(self):
        d = self.data
        path = d.session.path
        result = d.test_result
        output = Options()

        def testcases(seq):
            return [x[0] for x in seq if isinstance(x[0], unittest.TestCase)]

        output.summary = Options()
        output.summary.total = result.testsRun
        output.summary.failed = len(testcases(result.failures))
        output.summary.errors = len(testcases(result.errors))
        output.summary.blocked = len(testcases(chain(*result.blocked.values())))
        output.summary.skipped = len(testcases(result.skipped))

        output.duration = d.time.delta.total_seconds()
        output.start = int(d.time.start.strftime('%s'))
        output.stop = int(d.time.stop.strftime('%s'))
        output.runner = d.test_runner_ip
        output.url = d.session_url
        # {{ dut.device.alias }} - {{ dut.device.address }}: {{ dut.platform }} {{ dut.version.version }} {{ dut.version.build }} {{ dut.project }} {% if data and data.cores[dut.device.alias] %}[CORED]{% endif %}
        output.duts = [dict(alias=x.device.alias, address=x.device.address,
                            is_default=x.device.is_default(),
                            platform=x.platform, version=x.version.version,
                            build=x.version.build, product=x.version.product.to_tmos,
                            project=x.project, has_cored=d.cores.data.get(x.device.alias, False) if d.cores.data else False)
                       for x in d.duts]
        output.testrun_data = d.config.testrun

        output.results = []
        for result, status in [(result.failures, 'FAILED'),
                               (result.errors, 'ERROR'),
                               (map(lambda x: x[:2], chain(*result.blocked.values())), 'BLOCKED'),
                               (result.skipped, 'SKIPPED'),
                               (d.result.passed, 'PASSED')]:
            for test, err in result:
                if not isinstance(test, unittest.TestCase):
                    continue
                _, module, method = test.address()
                address = '%s:%s' % (module, method)

                tb = None
                if isinstance(err, tuple):
                    message = str(err[1])
                    tb = ''.join(traceback.format_exception(*err))
                elif isinstance(err, Exception):
                    message = str(err)
                else:
                    message = err
                testMethod = getattr(test.test, test.test._testMethodName)
                try:
                    loc = len(inspect.getsourcelines(testMethod)[0])
                    size = len(inspect.getsource(testMethod))
                except IOError:  # IOError:source code not available
                    loc = size = -1

                r = Options()
                r.name = address
                r.status = status
                r.author = getattr(test.test, 'author', None)
                r.rank = getattr(test.test, 'rank', None)
                r.message = message
                r.traceback = tb
                r.loc = loc
                r.size = size
                if hasattr(test, '_start'):
                    r.start = test._start
                    r.stop = test._stop
                else:
                    LOG.debug('No timestamp for %s', test)
                output.results.append(r)

        if os.path.exists(path):
            with open(os.path.join(path, self.filename), 'wt') as f:
                json.dump(output, f, indent=4)

    def finalize(self, result):
        self.dump_json()
