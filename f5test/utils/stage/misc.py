'''
Created on Feb 21, 2014

@author: jono
'''
import logging

from nose.config import _bool

import f5test.commands.shell as SCMD
import f5test.commands.rest as RCMD

from ...interfaces.ssh import SSHInterface
from ...macros.base import Macro
from .base import Stage


LOG = logging.getLogger(__name__)


class TweaksStage(Stage, Macro):
    """
    Mainly this stage is open for any type of debugging flags/setups needed to
    be set after a clean software install. This includes:

    - Enable iControl debug logging (icontrol);
    - Force logrotate (logrotate);
    - Enable iControl Proxy.

    These settings will be on for all tests and will not be unset (unless a
    teardown stage is implemented).
    """
    name = 'tweaks'

    def __init__(self, device, specs=None, *args, **kwargs):
        self.device = device
        self.specs = specs
        self._context = specs.get('_context')
        super(TweaksStage, self).__init__(*args, **kwargs)

    def setup(self):
        super(TweaksStage, self).setup()
        LOG.info('Tweaks stage for: %s', self.device)
        # mcp: Enable MCPD debug logging
        if self.specs.mcp and _bool(self.specs.mcp):
            with SSHInterface(device=self.device) as sshifc:
                sshifc.api.run('setdb log.mcpd.level debug')

        # icontrol: Enable icontrol debug logging
        if self.specs.icontrol and _bool(self.specs.icontrol):
            with SSHInterface(device=self.device) as sshifc:
                sshifc.api.run('setdb icontrol.loglevel debug')
                sshifc.api.run('bigstart restart httpd')

        # logrotate: Force logrotate all logs
        if self.specs.logrotate and _bool(self.specs.logrotate):
            with SSHInterface(device=self.device) as sshifc:
                sshifc.api.run('/usr/sbin/logrotate /etc/logrotate.conf -f')
                # BIG-IQ is so "special" - it doesn't use the usual logrotate ways.
                # 07/24 IT: restarting restjavad causes errors in discovery
                # sshifc.api.run('[ -f /service/restjavad/run ] && bigstart stop restjavad && rm -f /var/log/restjavad* && bigstart start restjavad')

        # log_finest: Force restjavad log files to use FINEST level.
        if self.specs.log_finest and _bool(self.specs.log_finest):
            with SSHInterface(device=self.device) as sshifc:
                sshifc.api.run("sed -i 's/^.level=.*/.level=FINEST/g' /etc/restjavad.log.conf && bigstart restart restjavad")

        # scp: Copy files to/from
        if self.specs.scp:
            params = self.specs.scp

            source = params.source if isinstance(params.source, basestring) \
                else ' '.join(params.source)

            with SSHInterface(device=self.device) as sshifc:
                if params.method.lower() == 'get':
                    SCMD.ssh.scp_get(ifc=sshifc, source=source,
                                     destination=params.destination, nokex=True)
                elif params.method.lower() == 'put':
                    SCMD.ssh.scp_put(ifc=sshifc, source=source,
                                     destination=params.destination, nokex=True)
                else:
                    raise ValueError("Unknown scp method: %s" % params.method)

        # shell: Execute shell commands
        if self.specs.shell:
            commands = [self.specs.shell] if isinstance(self.specs.shell,
                                                        basestring) \
                else self.specs.shell
            with SSHInterface(device=self.device) as sshifc:
                for command in commands:
                    ret = sshifc.api.run(command)
                    LOG.debug(ret)


class RebootStage(Stage, Macro):
    """
    Reboot a device and wait for mcpd/prompt to come back. Optionally wait for
    restjavad to come up.
    """
    name = 'reboot'
    timeout = 180

    def __init__(self, device, specs=None, *args, **kwargs):
        self.device = device
        self.specs = specs
        self._context = specs.get('_context')
        super(RebootStage, self).__init__(*args, **kwargs)

    def _wait_after_reboot(self, device):
        ssh = SSHInterface(device=device)

        timeout = self.timeout
        try:
            SCMD.ssh.GetPrompt(ifc=ssh).\
                run_wait(lambda x: x not in ('INOPERATIVE', '!'), timeout=timeout,
                         timeout_message="Timeout ({0}s) waiting for a non-inoperative prompt.")
            SCMD.ssh.FileExists('/var/run/mcpd.pid', ifc=ssh).\
                run_wait(lambda x: x,
                         progress_cb=lambda x: 'mcpd not up...',
                         timeout=timeout)
            SCMD.ssh.FileExists('/var/run/mprov.pid', ifc=ssh).\
                run_wait(lambda x: x is False,
                         progress_cb=lambda x: 'mprov still running...',
                         timeout=timeout)
            SCMD.ssh.FileExists('/var/run/grub.conf.lock', ifc=ssh).\
                run_wait(lambda x: x is False,
                         progress_cb=lambda x: 'grub.lock still running...',
                         timeout=timeout)
            version = SCMD.ssh.get_version(ifc=ssh)
        finally:
            ssh.close()
        return version

    def setup(self):
        super(RebootStage, self).setup()
        LOG.info('Reboot stage for: %s', self.device)
        SCMD.ssh.reboot(device=self.device)

        if self.specs.mcpd and _bool(self.specs.mcpd):
            self._wait_after_reboot(self.device)

        if self.specs.restjavad and _bool(self.specs.restjavad):
            RCMD.system.wait_restjavad([self.device])
