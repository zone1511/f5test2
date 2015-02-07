'''
Created on Aug 29, 2014

@author: jono
'''
import logging
from ...base import AttrDict

from . import ExtendedPlugin, PLUGIN_NAME

LOG = logging.getLogger(__name__)

TEST_SET_RUNS_URI = '/api/v1/run-requests/%s/test-set-runs'
RUN_RESULT_URI = '/api/v1/test-set-runs/%s/result'
FRAMEWORK_NAME = 'f5test'


class Atom(ExtendedPlugin):
    """
    Send ATOM report.
    """
    enabled = True

    def options(self, parser, env):
        """Register command line options."""
        parser.add_option('--with-atom', action='store_true',
                          dest='with_atom', default=False,
                          help="Enable ATOM reporting. (default: no)")
        parser.add_option('--with-atom-no-go', action='store',
                          help="Report not-run and skip everything (e.g. This version is not supported)")

    def configure(self, options, noseconfig):
        super(Atom, self).configure(options, noseconfig)
        from ...interfaces.testcase import ContextHelper
        self.data = ContextHelper().set_container(PLUGIN_NAME)
        self.enabled = noseconfig.options.with_atom
        self.context = ContextHelper(self.name)

    @property
    def dut(self):
        sshifc = self.context.get_ssh()
        return AttrDict(platform=sshifc.api.run('qp').stdout.strip())

    def create_test_set_run(self, site, reason=None):
        LOG.info("Starting a new test-set-run...")
        if not site.request_id:
            LOG.warning("A request-id is needed for all ATOM runs.")
            return
        url = TEST_SET_RUNS_URI % site.request_id

        rstifc = self.context.get_rest(url=site.url)
        payload = AttrDict()
        payload.testset = site.name
        payload.platform = self.dut.platform

        if reason:
            payload.result = {}
            payload.result.value = "not run"
            payload.result.notes = reason

        session = self.context.get_config().get_session()
        payload.framework_run = {}
        payload.framework_run.details_link = session.get_url()
        payload.framework_run.name = FRAMEWORK_NAME
        payload.framework_run.run_id = session.name
        try:
            resp = rstifc.api.post(url, payload=payload)
            site.run_id = resp.id
        except Exception, e:
            LOG.warning(e)

    def report_results(self, site):
        ctx = self.data
        if not site.run_id:
            return
        LOG.info("Reporting results to %s...", site.url)

        url = RUN_RESULT_URI % site.run_id
        result = ctx.test_result
        passed = result.wasSuccessful()
        notes = "Total: %d, Fail: %d" % \
            (ctx.test_result.testsRun - result.notFailCount(),
             result.failCount())

        rstifc = self.context.get_rest(url=site.url)
        payload = AttrDict()
        payload.value = 'pass' if passed else 'fail'
        payload.platform = ctx.dut.platform
        payload.notes = notes
        payload.framework_run = AttrDict(name='f5test', run_id=ctx.session.session)
        payload.framework_run.details_link = ctx.session_url

        try:
            rstifc.api.post(url, payload=payload)
        except Exception, e:
            LOG.warning(e)

    def prepareTest(self, test):
        from unittest.case import TestCase
        from unittest.suite import TestSuite
        options = self.data.nose_config.options

        def setUp():
            raise AssertionError("Execution blocked. Reason: %s" % options.with_atom_no_go)

        class FakeTest(TestCase):
            def runTest(this):  # @NoSelf
                this.skipTest(options.with_atom_no_go)

        if options.with_atom_no_go and isinstance(test, TestSuite):
            #    print test.countTestCases()
            test.context = FakeTest
            test._tests = []
            test.addTest(FakeTest())
            test.setUp = setUp

    def prepareTestResult(self, result):
        options = self.data.nose_config.options
        result.failfast = bool(options.with_atom_no_go)

    def begin(self):
        config = self.options
        options = self.data.nose_config.options

        if options.with_atom_no_go:
            self.create_test_set_run(config.bigip, options.with_atom_no_go)
        else:
            self.create_test_set_run(config.bigip)

    def finalize(self, result):
        config = self.options

        try:
            if not result.failfast:
                self.report_results(config.bigip)
        finally:
            self.context.teardown()
