from __future__ import absolute_import
import logging
from . import ExtendedPlugin, PLUGIN_NAME
from f5test.utils.parsers.logs import GrepLogTester
import csv
import os

LOG = logging.getLogger(__name__)
DEFAULT_DUTS = []
LOGNAME = '/var/log/restjavad.0.log'
OUTPUTFILE = 'warningsevere.csv'


class DutLogCheck(ExtendedPlugin):
    """
    Check main DUT's log for WARNING and SEVERE messages and report them
    in the CSV file specified in OUTPUTFILE
    """
    enabled = False
    name = "dut_log_check"

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in, find the default dut and retrieve
        an ssh interface for the default dut"""
        super(DutLogCheck, self).configure(options, noseconfig)
        from ...interfaces.config import ConfigInterface
        from ...interfaces.testcase import ContextHelper

        self.cfgifc = ConfigInterface()
        self.context = ContextHelper()
        self.tests = []
        self.data = ContextHelper().set_container(PLUGIN_NAME)

    def startTest(self, test, blocking_context):
        """Set up log checker for main dut log"""

        # Watch log for warnings and severe messages
        self.warnlog = GrepLogTester(LOGNAME,
                                     self.default_ssh_ifc, 'WARNING').setup()
        self.sevlog = GrepLogTester(LOGNAME,
                                    self.default_ssh_ifc, 'SEVERE').setup()

    def stopTest(self, test):
        """Check for warning/severe messages in main dut log"""

        # Check for warnings and severe messages in log
        warning = self.warnlog.teardown()
        severe = self.sevlog.teardown()

        # Create a test entry to add to the test collection for reporting
        testdata = {}
        testdata['test'] = test
        testdata['warn'] = warning
        testdata['sev'] = severe

        self.tests.append(testdata)

    def begin(self):
        """Open SSH connection for default dut
        """
        self.default_ssh_ifc = self.context.get_ssh()

    def finalize(self, result):
        """Close SSH connection for default dut, and write CSV file with
           aggregated results.
        """
        self.context.teardown()
        d = self.data
        path = d.session.path
        if os.path.exists(path):
            with open(os.path.join(path, OUTPUTFILE), 'wb') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(('Test Name', 'Warning', 'Severe'))
                for test in self.tests:
                    csvwriter.writerow((test['test'], len(test['warn']),
                                        len(test['sev'])))
                    for entry in test['warn']:
                        csvwriter.writerow((entry,))
                    for entry in test['sev']:
                        csvwriter.writerow((entry,))
                    # Blank row to make results more readable
                    csvwriter.writerow(('',))
