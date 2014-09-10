'''
Created on Aug 28, 2014

@author: jono
'''
import inspect
import json
import logging
import os
import traceback

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
        output = Options()
        output.summary = Options()
        output.summary.total = d.test_result.testsRun
        output.summary.failed = len(d.result.failures)
        output.summary.errors = len(d.result.errors)
        output.summary.skipped = len(d.result.skipped)

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
        for result, status in [(d.result.failures, 'FAILED'),
                               (d.result.errors, 'ERROR'),
                               (d.result.skipped, 'SKIPPED'),
                               (d.result.passed, 'PASSED')]:
            for test in result:
                _, module, method = test[0].address()
                address = '%s:%s' % (module, method)
                message = None if len(test) == 1 else \
                    str(test[1][1].message).strip()
                tb = None if len(test) == 1 else \
                    ''.join(traceback.format_exception(*test[1]))
                testMethod = getattr(test[0].test, test[0].test._testMethodName)
                loc = len(inspect.getsourcelines(testMethod)[0])
                size = len(inspect.getsource(testMethod))

                output.results.append(dict(name=address, status=status,
                                           author=getattr(test[0].test, 'author', None),
                                           message=message, traceback=tb,
                                           loc=loc, size=size)
                                      )

        if os.path.exists(path):
            with open(os.path.join(path, self.filename), 'wt') as f:
                json.dump(output, f, indent=4)

    def finalize(self, result):
        self.dump_json()
