#!/usr/bin/env python
'''
Created on Jun 3, 2011

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
from f5test.interfaces.subprocess import ShellInterface
import os
import inspect
import time
import logging


DISPLAY = ':99'
SELENIUM_JAR = 'selenium-server-standalone.jar'
LOG = logging.getLogger(__name__)
__version__ = '0.3'


class SeleniumRC(Macro):

    def __init__(self, options, action):
        self.options = Options(options.__dict__)
        self.action = action

        if options.env:
            venv_dir = options.env
            bin_dir = os.path.join(venv_dir, 'bin')
        else:
            bin_dir = os.path.dirname(os.path.realpath(inspect.stack()[-1][1]))
            venv_dir = os.path.dirname(bin_dir)

        LOG.info('Using sandbox directory: %s', venv_dir)
        params = Options()
        params.display = options.display
        
        jar_file = os.path.join(bin_dir, SELENIUM_JAR)
        params.jar = "-jar %s" % jar_file
        assert os.path.exists(jar_file), '%s not found' % jar_file
        
        var_run = os.path.join(venv_dir, 'var', 'run')
        var_log = os.path.join(venv_dir, 'var', 'log')
        if not os.path.exists(var_run):
            os.makedirs(var_run)
        
        if not os.path.exists(var_log):
            os.makedirs(var_log)
        
        params.dirs = dict(run=var_run,
                           log=var_log,
                           bin=bin_dir)
        
        params.pids = dict(xvfb='xvfb.pid',
                           selenium='selenium.pid', 
                           selenium_node='selenium_node.pid',
                           selenium_hub='selenium_hub.pid')

        params.logs = dict(xvfb='xvfb.log',
                           selenium='selenium.log', 
                           selenium_node='selenium_node.log',
                           selenium_hub='selenium_hub.log')

        if self.options.hub:
            params.hub = "-hub http://%s:4444/grid/register" % self.options.hub
            if not self.options.role:
                self.options.role = 'node'
        else:
            params.hub = ''

        if self.options.role:
            if self.options.role == 'hub':
                self.options.no_xvfb = True
            
            if self.options.role == 'node' and not self.options.hub:
                raise ValueError('--hub needs to be specified')
            
            params.role = "-role %s" % self.options.role
        else:
            params.role = ''
        
        self.params = params
        super(SeleniumRC, self).__init__()

    def do_kill_wait(self, pid, signal, timeout=10, interval=0.1):
        os.kill(pid, signal)
        now = start = time.time()
        
        while now - start < timeout:
            try:
                os.kill(pid, 0)
            except OSError:
                break
            
            time.sleep(interval)
            now = time.time()
        else:
            LOG.error('Timeout waiting for PID %d to finish.', pid)

    def do_start_xvfb(self, shell, params, env):
        pid_file = os.path.join(params.dirs.run, params.pids.xvfb)
        log_file = os.path.join(params.dirs.log, params.logs.xvfb)
        
        if not self.options.force and os.path.exists(pid_file):
            LOG.error('Selenium pid file exists: %s Stop first or use --force to override.', pid_file)
            return

        proc = shell.api.run('Xvfb -ac -extension GLX +render %(display)s -screen 0 1366x768x24' % params, 
                             env=env, fork=True,
                             stream=open(log_file, 'w'))
        
        LOG.info('Xvfb pid: %d', proc.pid)
        with file(pid_file, 'w') as f:
            f.write(str(proc.pid))

    def do_start_selenium(self, shell, params, env):
        if self.options.role:
            if self.options.role == 'hub':
                pid_file = params.pids.selenium_hub
                log_file = params.logs.selenium_hub
            else:
                pid_file = params.pids.selenium_node
                log_file = params.logs.selenium_node
        else:
            pid_file = params.pids.selenium
            log_file = params.logs.selenium

        pid_file = os.path.join(params.dirs.run, pid_file)
        log_file = os.path.join(params.dirs.log, log_file)
        
        if not self.options.force and os.path.exists(pid_file):
            LOG.error('Selenium pid file exists: %s. Stop first or use --force to override.', pid_file)
            return

        proc = shell.api.run('java %(jar)s %(role)s %(hub)s' % params, 
                             env=env, fork=True, 
                             stream=open(log_file, 'w'))
        
        LOG.info('Selenium pid: %d', proc.pid)
        with file(pid_file, 'w') as f:
            f.write(str(proc.pid))

    def stop(self):
        LOG.info('Stopping...')
        params = self.params
        
        for pid_file in params.pids.values():
            pid_file = os.path.join(params.dirs.run, pid_file)
            if os.path.exists(pid_file):
                pid = int(open(pid_file).read())
                LOG.info('Sending SIGTERM to: %d', pid)
                try:
                    self.do_kill_wait(pid, 15)
                except OSError, e:
                    LOG.warning(e)
                finally:
                    os.remove(pid_file)

    def start(self):
        LOG.info('Starting...')
        params = self.params
        
        with ShellInterface(timeout=self.options.timeout) as shell:
            os.environ.update({'DISPLAY': params.display})
            env = os.environ
            is_remote = bool(params.display.split(':')[0])

            # Open the log file and leave it open so the process can still write
            # while it's running.
            if not self.options.no_xvfb and not is_remote:
                self.do_start_xvfb(shell, params, env)

            if not self.options.no_selenium:
                self.do_start_selenium(shell, params, env)

    def setup(self):
        if self.action == 'start':
            return self.start()
        elif self.action == 'stop':
            return self.stop()
        elif self.action == 'restart':
            self.stop()
            self.start()
        else:
            ValueError('Unknown action: %s' % self.action)


def main():
    import optparse
    import sys

    usage = """%prog [options] <action>"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2, 
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="Selenium RC Tool v%s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages")
    
    p.add_option("-d", "--display", metavar="DISPLAY",
                 default=DISPLAY, type="string",
                 help="The display to be used (default: %s)" % DISPLAY)
    p.add_option("-e", "--env", metavar="DIRECTORY", type="string",
                 help="The sandbox directory (default: .)")
    p.add_option("-t", "--timeout", metavar="TIMEOUT", type="int", default=60,
                 help="Timeout. (default: 60)")
    p.add_option("", "--no-xvfb", action="store_true",
                 help="Don't start Xvfb.")
    p.add_option("", "--no-selenium", action="store_true",
                 help="Don't start Selenium Server.")
    p.add_option("", "--force", action="store_true",
                 help="Overwrite pid files.")
    p.add_option("-r", "--role", metavar="ROLE", type="string",
                 help="Selenium role. Can be either node or hub. (default: standalone)")
    p.add_option("", "--hub", metavar="IP", type="string",
                 help="Selenium Grid hub url.")

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        #logging.getLogger('paramiko.transport').setLevel(logging.ERROR)
        logging.getLogger('f5test').setLevel(logging.ERROR)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)
    
    if not args or args[0] not in ('start', 'stop', 'restart'):
        p.print_version()
        p.print_help()
        sys.exit(2)

    cs = SeleniumRC(options=options, action=args[0])
    cs.run()


if __name__ == '__main__':
    main()
