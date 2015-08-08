'''
Created on Jan 4, 2012
Modified on: $DateTime: 2015/05/11 10:06:16 $

@author: jono
'''
import re
import logging
from f5test.utils.wait import wait
from f5test.base import AttrDict
from f5test.interfaces.ssh import SSHInterface

LOG = logging.getLogger(__name__)


class LogTester(object):
    """The generic LogTester class that lets you implement a callback function.
    It also has an embedded wait which waits until the provided callback returns true."""

    def __init__(self, filename, testcb, ifc, timeout=0):
        self.filename = filename
        self.testcb = testcb
        self.timeout = timeout
        self.ifc = ifc

    def __enter__(self):
        self.setup()

    def __exit__(self, type, value, traceback):  # @ReservedAssignment
        # If there is an exception inside the context block reraise it and don't
        # bother tailing the log.
        if type:
            return False
        self.teardown()

    def setup(self):
        ssh = self.ifc.api
        self._pre_stats = ssh.stat(self.filename)
        return self

    def teardown(self):
        ssh = self.ifc.api

        def callback():
            self._post_stats = ssh.stat(self.filename)

            size_before = self._pre_stats.st_size
            size_after = self._post_stats.st_size
            delta = size_after - size_before
            LOG.debug('delta: %d', delta)

            ret = ssh.run('tail --bytes={0} {1}'.format(delta, self.filename))
            return self.testcb(ret.stdout, self._post_stats)

        if self.timeout:
            return wait(callback, timeout=self.timeout)
        else:
            return callback()


class LogsTester(LogTester):
    """The LogsTester class inherits LogTester and allow you to look at logs
    from multiple devices.
    """

    def __init__(self, filename, testcb, devices, timeout=0):
        self.filename = filename
        self.testcb = testcb
        self.timeout = timeout
        self.devices = devices

    def setup(self):
        self._pre_stats = AttrDict()
        for device in self.devices:
            with SSHInterface(device=device) as ifc:
                ssh = ifc.api
                self._pre_stats[device] = ssh.stat(self.filename)
        return self

    def teardown(self):
        def callback():
            ret = AttrDict()
            self._post_stats = AttrDict()

            for device in self.devices:
                with SSHInterface(device=device) as ifc:
                    ssh = ifc.api
                    self._post_stats[device] = ssh.stat(self.filename)

                    size_before = self._pre_stats[device].st_size
                    size_after = self._post_stats[device].st_size
                    delta = size_after - size_before
                    LOG.debug('delta: %d', delta)

                    resp = ssh.run('tail --bytes={0} {1}'.format(delta,
                                                                 self.filename))
                    ret[device] = resp.stdout

            return self.testcb(ret, self._post_stats)

        if self.timeout:
            return wait(callback, timeout=self.timeout)
        else:
            return callback()


class GrepLogTester(LogTester):
    """A more specific LogTester class that greps the log delta for a specific regex pattern"""

    def __init__(self, filename, ifc, expr=r'.*'):
        self.filename = filename
        self.ifc = ifc
        self.timeout = None

        def testcb(stdout, stats):
            lines = []
            for line in stdout.splitlines():
                if re.search(expr, line):
                    lines.append(line)
            return lines
        self.testcb = testcb
