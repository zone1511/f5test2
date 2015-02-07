'''
Created on Dec 19, 2014

@author: jono
'''
import logging
from . import ExtendedPlugin
from ...interfaces.testcase import ContextHelper
from ...interfaces.config import expand_devices
from ...interfaces.rest.emapi.objects.shared import DeviceInfo
import f5test.commands.icontrol as ICMD


LOG = logging.getLogger(__name__)
TIMEOUT = 5


class TestBed(ExtendedPlugin):
    """
    Setup the test bed. Ping DUTs, print version/platform information, disable
    unreachable DUTs, etc.
    """
    enabled = True

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--without-testbed', action='store_true',
                          default=False,
                          help="Disable testbed plugin. (default: yes)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        super(TestBed, self).configure(options, noseconfig)

        if noseconfig.options.without_testbed:
            self.enabled = False

        self.context = ContextHelper()
        cfgifc = self.context.get_config()
        self.duts = expand_devices(options.get('duts',
                                               cfgifc.config.
                                               get('plugins', {}).
                                               get('_default_', {}).
                                               get('duts', [])))

    def disable_unreachable_duts(self, duts):
        opt = self.options
        LOG.info('Pinging DUTs...')
        for device in duts:
            icifc = self.context.get_icontrol(device=device,
                                              timeout=opt.get('timeout', TIMEOUT))
            rstifc = self.context.get_icontrol_rest(device=device,
                                                    timeout=opt.get('timeout',
                                                                    TIMEOUT))
            try:
                # Very basic health check via an iControl call
                version = icifc.api.System.SystemInfo.get_version()
                if version >= 'BIG-IP_v11.5.0':
                    # Very basic health check via an REST API call
                    rstifc.api.get(DeviceInfo.URI)
            except Exception, e:
                device.enabled = False
                # self.duts.remove(device)
                LOG.warning('Disabling unreachable DUT: %s (%s)', device, e)

    def query_duts(self, duts):
        opt = self.options
        version = platform = ''
        i = 1
        LOG.info('=' * 80)
        LOG.info('Test environment:')
        LOG.info('-' * 80)
        for device in self.duts:
            bits = []
            if device.enabled:
                if opt.query and opt.query.get('platform', False):
                    platform = ICMD.system.get_platform(device=device)
                    bits.append(platform)

                if opt.query and opt.query.get('version', False):
                    version = ICMD.system.get_version(device=device)
                    bits.append(str(version))
            else:
                bits.append('Unreachable!')

            LOG.info("%s: %s" % (device, ', '.join(bits)))
            i += 1

        LOG.info('=' * 80)

    def begin(self):
        opt = self.options

        if opt.get('disable unreachable', False):
            self.disable_unreachable_duts(self.duts)

        self.query_duts(self.duts)

    def finalize(self, result):
        self.context.teardown()
