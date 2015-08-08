'''
Created on Feb 4, 2015

@author: jono
'''
import logging
from . import ExtendedPlugin
from ...interfaces.testcase import ContextHelper
from ...interfaces.config import expand_devices
from ...utils.cm import isofile
from ...utils.version import Product
import os
import f5test.commands.shell as SCMD
import f5test.commands.rest as RCMD
from ...base import AttrDict
import json


LOG = logging.getLogger(__name__)
TIMEOUT = 5
PROJECT = 'bigiq-mgmt'
RPM_FILE = 'jacoco-*.rpm'
JACOCO_PACKAGE = 'jacoco-'
DESTINATION = '/tmp'
TRIGGER_FILE = '/service/restjavad/jacoco'
EXEC_FILE = '/shared/tmp/jacoco.exec'
JACOCO_HOST = '10.145.194.1'
JAR_DIR = '/usr/share/java/rest'
JARS = ['f5.rest.adc.shared.jar', 'f5.rest.asm-bigiq.jar',
        'f5.rest.autodeploy.jar', 'f5.rest.bigiq-adc-core-config.jar',
        'f5.rest.avr.jar', 'f5.rest.bigiq-adc.jar', 'f5.rest.cloud.jar',
        'f5.rest.em.jar', 'f5.rest.indexing.jar', 'f5.rest.jar',
        'f5.rest.security.afm.jar', 'f5.rest.security.asm.jar',
        'f5.rest.security.base.jar', 'f5.rest.security.common.jar',
        'f5.rest.security.shared.jar', 'f5.rest.security.websafe.jar']
JAR_BUNDLE = '/tmp/jacoco_jars.tar.gz'


class Jacoco(ExtendedPlugin):
    """
    Install jacoco RPM, enable it and collect results.
    """
    enabled = False

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--with-jacoco', action='store_true',
                          help="Enable jacoco plugin. (default: no)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        super(Jacoco, self).configure(options, noseconfig)

        self.context = ContextHelper()
        if options.get('duts'):
            self.duts = expand_devices(options.duts)
        else:
            cfgifc = self.context.get_config()
            self.duts = [cfgifc.get_device()]
        self.is_installed = False

    def make_dirs(self, device):
        session = self.context.get_config().get_session()
        path = os.path.join(session.path, 'jacoco',
                            device.get_address())
        path = os.path.expanduser(path)
        path = os.path.expandvars(path)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def jenkins_upload(self, sshifc):
        session = self.context.get_config().get_session()
        filename = 'jacoco.exec.%s' % sshifc.address
        with self.context.get_rest(proto='http', address=JACOCO_HOST, port=8080) as rstifc:
            # Force to Connection: close. There seems to be a problem with Jetty & keep-alive.
            rstifc.api.no_keepalive = True

            LOG.info('Uploading jacoco.exec to Jenkins...')
            headers = {'Content-Type': 'multipart/form-data',
                       'Transfer-Encoding': 'chunked'}
            payload = AttrDict()
            payload.parameter = []
            payload.parameter.append(dict(name='id', value=session.name))
            payload.parameter.append(dict(name='fileName', value=filename))
            payload.parameter.append(dict(name='branch', value='foo'))
            payload.parameter.append(dict(name='version', value='foo'))
            payload.parameter.append(dict(name='jacoco.exec', file='file0'))
            s = json.dumps(payload)
            with sshifc.api.sftp().open(EXEC_FILE) as f:
                # restkit expects the file object to have a name attr
                f.name = filename
                rstifc.api.post('/job/ITE-management-adc-add-code-coverage/build',
                                headers=headers, payload={'json': s, 'file0': f})

            # Upload .jars bundle here
            LOG.info('Uploading jars pack to Jenkins...')
            filename = os.path.basename(JAR_BUNDLE)
            payload.parameter = []
            payload.parameter.append(dict(name='id', value=session.name))
            payload.parameter.append(dict(name='fileName', value=filename))
            payload.parameter.append(dict(name='branch', value='foo'))
            payload.parameter.append(dict(name='version', value='foo'))
            payload.parameter.append(dict(name='jacoco.exec', file='file0'))
            s = json.dumps(payload)

            with sshifc.api.sftp().open(JAR_BUNDLE) as f:
                # restkit expects the file object to have a name attr
                f.name = filename
                rstifc.api.post('/job/ITE-management-adc-add-code-coverage/build',
                                headers=headers, payload={'json': s, 'file0': f})

            # Trigger a coverage report task
            payload.parameter = []
            payload.parameter.append(dict(name='id', value=session.name))
            s = json.dumps(payload)
            rstifc.api.post('/job/ITE-management-adc-run-code-coverage/build',
                            headers=headers, payload={'json': s})

    def startTest(self, test, blocking_context=None):
        """Install RPM on DUTs (only once)"""
        if not self.is_installed:
            LOG.info('Enabling jacoco on DUTs...')
            for dut in self.duts:
                with self.context.get_ssh(device=dut) as sshifc:
                    if not sshifc.api.exists(TRIGGER_FILE):
                        iso = isofile(PROJECT, product=Product.BIGIQ)
                        root = os.path.dirname(iso)
                        jacoco_rpm = os.path.join(root, 'RPMS', 'noarch', RPM_FILE)
                        SCMD.ssh.scp_put(ifc=sshifc, source=jacoco_rpm,
                                         destination=DESTINATION, nokex=True)
                        try:
                            sshifc.api.run('bigstart stop restjavad')
                            if sshifc.api.exists(EXEC_FILE):
                                sshifc.api.remove(EXEC_FILE)
                            sshifc.api.run('tar -C {} -czvf {} {}'.format(JAR_DIR, JAR_BUNDLE, ' '.join(JARS)))
                            sshifc.api.run('mount -n -o remount,rw /usr')
                            sshifc.api.run('touch {}'.format(TRIGGER_FILE))
                            sshifc.api.run('rpm -Uvh {}'.format(os.path.join(DESTINATION,
                                                                             RPM_FILE)))
                        finally:
                            sshifc.api.run('mount -n -o remount,ro /usr')
                            sshifc.api.run('bigstart start restjavad')
            RCMD.system.wait_restjavad(self.duts)
            self.is_installed = True

    def finalize(self, result):
        """Collect jacoco.exec results"""
        if self.is_installed:
            for dut in self.duts:
                LOG.info('Collecting jacoco results from %s...', dut)
                with self.context.get_ssh(device=dut) as sshifc:
                    if sshifc.api.exists(TRIGGER_FILE):
                        try:
                            sshifc.api.run('bigstart stop restjavad')
                            sshifc.api.remove(TRIGGER_FILE)
                            sshifc.api.run('mount -n -o remount,rw /usr')
                            sshifc.api.run('rpm -e {}'.format(JACOCO_PACKAGE))
                        finally:
                            sshifc.api.run('mount -n -o remount,ro /usr')
                            sshifc.api.run('bigstart start restjavad')
                            self.is_installed = False

                    # Download the .exec file
#                     path = self.make_dirs(dut)
#                     SCMD.ssh.scp_get(ifc=sshifc, source=EXEC_FILE,
#                                      destination=path, nokex=True)

                    self.jenkins_upload(sshifc)
                    sshifc.api.run('rm -f {}'.format(EXEC_FILE))

            RCMD.system.wait_restjavad(self.duts)
        self.context.teardown()
