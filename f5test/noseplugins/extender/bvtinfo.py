'''
Created on Aug 29, 2014

@author: jono
'''
import logging
import urllib
import urllib2

from . import ExtendedPlugin, PLUGIN_NAME

LOG = logging.getLogger(__name__)


class BvtInfo(ExtendedPlugin):
    """
    Send BVTInfo report.
    """
    enabled = True

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--with-bvtinfo', action='store_true',
                          dest='with_bvtinfo', default=False,
                          help="Enable BVTInfo reporting. (default: no)")
        parser.add_option('--with-bvtinfo-iq', action='store_true',
                          dest='with_bvtinfo_iq', default=False,
                          help="Enable BVTInfo-IQ reporting. (default: no)")

    def configure(self, options, noseconfig):
        super(BvtInfo, self).configure(options, noseconfig)
        from ...interfaces.testcase import ContextHelper
        self.data = ContextHelper().set_container(PLUGIN_NAME)
        self.enabled = noseconfig.options.with_bvtinfo or noseconfig.options.with_bvtinfo_iq

    def report_results(self, site):
        LOG.info("Reporting results to %s...", site.url)
        ctx = self.data
        config = self.data.config

        result = ctx.test_result
        if config.testopia and config.testopia._testrun:
            result_url = self.options.result_url % {'run_id': config.testopia._testrun}
        else:
            result_url = ctx.session_url
        result_text = "Total: %d, Fail: %d" % \
            (ctx.test_result.testsRun - result.notFailCount(),
             result.failCount())

        # Report each device
        for dut in ctx.duts:
            if not dut.version or not dut.platform:
                LOG.error("Can't submit results without version or platform.")
                continue

            LOG.info('BVTInfo report for: %s...', dut.device)
            project = dut.project or dut.version.version
            if dut.edition.startswith('Hotfix'):
                project = '%s-%s' % (project, dut.edition.split()[1].lower())

            # XXX: EM 3,0 is an oddball. /VERSION includes a project field and
            # bvtinfo project is called Em3.0.0 which is non-standard.
            if dut.version.product.is_em and \
               abs(dut.version) == 'em 3.0':
                project = 'Em3.0.0'

            params = urllib.urlencode(dict(
                bvttool=site.name,
                project=self.options.get('project', project),
                buildno=self.options.get('build', dut.version.build),
                test_pass=int(result.wasSuccessful()),
                platform=dut.platform,
                result_url=result_url,
                result_text=result_text
            ))

            LOG.debug(params)
            opener = urllib2.build_opener()
            urllib2.install_opener(opener)
            try:
                f = opener.open(site.url, params)
                data = f.read()
                f.close()
                LOG.info('BVTInfo result report successful: (%s)', data)
            except urllib2.HTTPError, e:
                LOG.error('BVTInfo result report failed: %s (%s)', e, e.read())
            except Exception, e:
                LOG.error('BVTInfo result report failed: %s', e)

    def finalize(self, result):
        bvtinfocfg = self.options
        options = self.data.nose_config.options

        if options.with_bvtinfo:
            self.report_results(bvtinfocfg.bigip)

        if options.with_bvtinfo_iq:
            self.report_results(bvtinfocfg.bigiq)
