'''
Created on Dec 30, 2014

@author: jwong
'''
from . import ExtendedPlugin, PLUGIN_NAME
from threading import Thread
from f5test.interfaces.config.core import ConfigInterface
from f5test.interfaces.ssh.core import SSHInterface
from f5test.interfaces.ssh.driver import SSHTimeoutError
from f5test.interfaces.testcase import ContextHelper
from socket import inet_aton
import f5test.commands.shell as SCMD
import logging
import os
import struct
import json


LOG = logging.getLogger(__name__)
TIMEOUT = 180
LOGS = ['/var/log/tmm*', '/var/log/ltm*', '/var/log/restjavad*',
        '/var/log/restnoded/*', '/var/service/restjavad/hs_err*.log']
FILE = '/var/tmp/restjavad.out'
STATS = ['top -b -n 1', 'iostat']
DIRECTORY = 'Scale'


class ScaleStatsCollector(Thread):

    def __init__(self, device, data):
        super(ScaleStatsCollector, self).__init__(name='ScaleStatsCollector@%s'
                                                  % device)
        self.device = device
        self.data = data
        self.session = ConfigInterface().get_session()

    def run(self):
        LOG.info('Getting Stats for Scale...')
        with SSHInterface(device=self.device, timeout=TIMEOUT) as sshifc:
            try:
                # Create directory for stats
                device_dir = self.device.get_address() + "-" + self.device.alias

                stat_dir = os.path.join(self.session.path, DIRECTORY,
                                        device_dir)
                stat_dir = os.path.expanduser(stat_dir)
                stat_dir = os.path.expandvars(stat_dir)
                if not os.path.exists(stat_dir):
                    os.makedirs(stat_dir)

                # Create directory for logs.
                log_dir = os.path.join(self.session.path, DIRECTORY,
                                       device_dir, 'log')
                log_dir = os.path.expanduser(log_dir)
                log_dir = os.path.expandvars(log_dir)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)

                # Collect specific files
                for log in LOGS:
                    ret = sshifc.api.run('ls -1 %s | wc -l' % log)
                    if not ret.status and int(ret.stdout):
                        SCMD.ssh.scp_get(ifc=sshifc, source=log,
                                         destination=log_dir)

                context = ContextHelper(__name__)
                r = context.get_icontrol_rest(device=self.device).api
                output = r.get('/mgmt/shared/diagnostics')
                with open(os.path.join(stat_dir, 'diagnostics'), 'wt') as f:
                    json.dump(output, f, indent=4)

                if SCMD.ssh.file_exists(ifc=sshifc, filename=FILE):
                    SCMD.ssh.scp_get(ifc=sshifc, source=FILE,
                                     destination=stat_dir)

                # Collect stats
                for stat in STATS:
                    output = SCMD.ssh.generic(stat, ifc=sshifc)
                    with open(os.path.join(stat_dir, stat.split()[0]), 'wt') as f:
                        f.write(output.stdout)

                java_pid = SCMD.ssh.generic("cat /service/restjavad/supervise/pid",
                                            ifc=sshifc).stdout
                output = SCMD.ssh.generic('lsof -p %s' % java_pid, ifc=sshifc)
                with open(os.path.join(stat_dir, 'lsof'), 'wt') as f:
                    f.write(output.stdout)

            except SSHTimeoutError:
                LOG.warning('Could not complete collecting log and stats on %s',
                            self.device)


class ScaleStats(ExtendedPlugin):
    """
    Collect the following:
        /var/log/*
        /var/tmp/restjavad.out

        lsof -p <PID> <PID> = java process
        top
        iostat

    """
    enabled = False

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--scale-stats', action='store_true',
                          dest='scale_stats', default=False,
                          help="Enable log and stat collecting. (default: False)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        super(ScaleStats, self).configure(options, noseconfig)
        self.data = ContextHelper().set_container(PLUGIN_NAME)
        self.context = ContextHelper(__name__)
        if noseconfig.options.scale_stats:
            self.enabled = True

    def finalize(self, result):
        pool = []
        context = ContextHelper(__name__)

        multiple = self.options.get('multiple', 10)
        count = 0

        sorted_duts = sorted(self.data.duts, key=lambda ip: struct.
                             unpack("!L", inet_aton(str(ip.device.address)))[0])
        for dut in sorted_duts:
            v = context.get_icontrol(device=dut.device).version
            if v.product.is_bigiq or count % multiple == 0:
                t = ScaleStatsCollector(dut.device, self.data)
                t.start()
                pool.append(t)

            if v.product.is_bigip:
                count += 1

        for t in pool:
            t.join(TIMEOUT + 10)
