#!/usr/bin/env python
'''
Created on May 26, 2011

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
from f5test.interfaces.config import DeviceAccess
from f5test.interfaces.ssh import SSHInterface
from f5test.interfaces.icontrol.em import EMInterface
import f5test.commands.shell.em as EMSQL
from f5test.defaults import ADMIN_PASSWORD, ADMIN_USERNAME, ROOT_PASSWORD, \
                            ROOT_USERNAME
import logging


LOG = logging.getLogger(__name__)
__version__ = '0.1'


class Big3dUtil(Macro):

    def __init__(self, options, address=None):
        self.options = Options(options.__dict__)

        self.sshparams = Options(device=self.options.device,
                         address=address, timeout=self.options.timeout,
                         username=self.options.root_username,
                         password=self.options.root_password)
        self.icparams = Options(device=self.options.device,
                         address=address, timeout=self.options.timeout,
                         username=self.options.admin_username,
                         password=self.options.admin_password)
        
        super(Big3dUtil, self).__init__()

    def setup(self):
        mgmtips = []
        for device in self.options.devices:
            if isinstance(device, basestring):
                mgmtips.append(device)
            elif isinstance(device, DeviceAccess):
                mgmtips.append(device.address)
            else:
                raise ValueError(device)
        
        assert mgmtips, 'No devices discovered on EM?'
        with SSHInterface(**self.sshparams) as sshifc:
            with EMInterface(**self.icparams) as emifc:
                emapi = emifc.api
                statuses = EMSQL.device.get_device_state(mgmtips, ifc=sshifc)
                uids = []
                for status in statuses:
                    if status.status in ('big3d_below_minimum', 'big3d_update_required') \
                    and status.refresh_failed_at is None:
                        uids.append(status.uid)
                
                
                if uids:
                    LOG.info('Big3d install on device_uids: %s', uids)
                    ret = emapi.big3d_install.big3dInstallCreate(self.options.task_name, 
                                                                 uids, 'true', 'true')
                    job = int(ret['jobUid'])
                    
                    task = EMSQL.device.GetBig3dTask(job, ifc=sshifc) \
                           .run_wait(lambda x: x['status'] != 'started',
                                     timeout=300,
                                     progress_cb=lambda x:'big3d install: %d%%' % x.progress_percent)
                    assert task.error_count == 0, 'Errors in big3d task: %s' % task
                    return task
                else:
                    LOG.info('No devices need big3d install')


def main():
    import optparse
    import sys

    usage = """%prog [options] <emaddress>"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2, 
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="Big3d Updater v%s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages")
    
    p.add_option("-u", "--admin-username", metavar="USERNAME",
                 default=ADMIN_USERNAME, type="string",
                 help="An user with admin rights (default: %s)"
                 % ADMIN_USERNAME)
    p.add_option("-p", "--admin-password", metavar="PASSWORD",
                 default=ADMIN_PASSWORD, type="string",
                 help="An user with admin rights (default: %s)"
                 % ADMIN_PASSWORD)
    p.add_option("-r", "--root-username", metavar="USERNAME",
                 default=ROOT_USERNAME, type="string",
                 help="An user with admin rights (default: %s)"
                 % ROOT_USERNAME)
    p.add_option("-a", "--root-password", metavar="PASSWORD",
                 default=ROOT_PASSWORD, type="string",
                 help="An user with admin rights (default: %s)"
                 % ROOT_PASSWORD)
    p.add_option("-d", "--devices", metavar="DEVICE", type="string", 
                 action="append",
                 help="Include only this device(s). Multiple occurrences allowed.")
    p.add_option("-n", "--task-name", metavar="STRING",
                 default='Big3d install task', type="string",
                 help="The task name.")
    
    p.add_option("-t", "--timeout", metavar="TIMEOUT", type="int", default=60,
                 help="Timeout. (default: 60)")

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        logging.getLogger('paramiko.transport').setLevel(logging.ERROR)
        logging.getLogger('f5test').setLevel(logging.INFO)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)
    
    if not args:
        p.print_version()
        p.print_help()
        sys.exit(2)
    
    cs = Big3dUtil(options=options, address=args[0])
    cs.run()


if __name__ == '__main__':
    main()
