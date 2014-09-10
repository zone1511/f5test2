#!/usr/bin/env python
'''
Created on May 26, 2011

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
from f5test.interfaces.ssh import SSHInterface
from f5test.interfaces.icontrol import IcontrolInterface
import f5test.commands.shell.sql as SQL
import f5test.commands.shell as SCMD
import f5test.commands.icontrol.em as EMAPI
from f5test.interfaces.icontrol.empython.MessageParser import ParsingError
from f5test.interfaces.icontrol.driver import IControlFault, IControlTransportError
from f5test.defaults import ROOT_PASSWORD, ROOT_USERNAME, ADMIN_USERNAME, \
    ADMIN_PASSWORD
from f5test.interfaces.icontrol.em import EMInterface
from netaddr import IPAddress
import logging


LOG = logging.getLogger(__name__)
UIDOFFSET = 1
IPOFFSET = 3000
START_IP = '10.10.0.0'
MAXSQL = 50
__version__ = '0.1'


class ClonerFailed(Exception):
    pass


class DeviceCloner(Macro):

    def __init__(self, options, emaddress=None, bigipaddress=None):
        self.options = Options(options)

        self.emparams = Options(device=self.options.emdevice,
                         address=emaddress, timeout=self.options.timeout,
                         username=self.options.em_root_username,
                         password=self.options.em_root_password)
        self.emicparams = Options(device=self.options.emdevice,
                         address=emaddress, timeout=self.options.timeout,
                         username=self.options.em_admin_username,
                         password=self.options.em_admin_password)
        self.bigipparams = Options(device=self.options.bigipdevice,
                         address=bigipaddress, timeout=self.options.timeout,
                         username=self.options.bigip_admin_username,
                         password=self.options.bigip_admin_password)

        super(DeviceCloner, self).__init__()

    def do_prep_insert(self, row):
        names = ['NULL' if x is None else unicode(x) for x in row.keys()]
        values = []
        for x in row.values():
            if x is None:
                values.append('NULL')
            else:
                values.append("'%s'" % unicode(x))
        return "(`%s`) VALUES(%s)" % ("`,`".join(names), ",".join(values))

    def do_get_template(self, mgmtip, ifc):
        # Select template row
        rows = SQL.query("SELECT * FROM device WHERE mgmt_address='%s';" % mgmtip, ifc=ifc)
        if not rows:
            raise ClonerFailed('Device with mgmtip %s not found.' % mgmtip)
        return rows[0]

    def do_inject(self):
        LOG.info('* Cloning mode *')
        bulk_sql = []
        ip_offset = self.options.ip_offset
        with EMInterface(**self.emicparams) as emicifc:
            LOG.info('Disable auto-refresh on EM...')
            EMAPI.device.set_config(auto_refresh=False, ifc=emicifc)

        with SSHInterface(**self.emparams) as emsshifc:
            version = SCMD.ssh.get_version(ifc=emsshifc)
            has_groups = version < 'em 2.3.0'
            rows = SQL.query('SELECT MAX(device.uid) AS device, MAX(device_slot.uid) AS slot FROM device, device_slot;', ifc=emsshifc)
            max_device_uid = int(rows[0].device)
            max_slot_uid = int(rows[0].slot)

            bpmgmt = self.bigipparams.address
            template = self.do_get_template(bpmgmt, emsshifc)
            assert template.access_address != template.mgmt_address, \
                    "Template device must be discovered by its self IP."
            device_uid = int(template.uid)
            LOG.info('Template: %s', template.host_name)
            start_ip = IPAddress(START_IP)
            LOG.info('Inserting device rows...')
            for i in range(1, self.options.clones + 1, 1):
                template.uid = max_device_uid + UIDOFFSET + i
                template.access_address = str(start_ip + ip_offset + i)
                template.system_id = None
                template.last_refresh = None
                query = "INSERT INTO `device` %s" % self.do_prep_insert(template)
                bulk_sql.append(query)
                if has_groups:
                    bulk_sql.append("INSERT INTO device_2_device_group VALUES (NULL,%d,1)" % template.uid)

            while bulk_sql:
                SQL.query(";".join(bulk_sql[:MAXSQL]), ifc=emsshifc)
                bulk_sql[:MAXSQL] = []

            # Prepare device slot
            rows = SQL.query("SELECT * FROM device_slot WHERE device_id=%d;" % device_uid, ifc=emsshifc)
            last_device_slot_uid = max_slot_uid + UIDOFFSET
            LOG.info('Inserting device_slot rows...')
            for row in rows:
                last_device_uid = max_device_uid + UIDOFFSET
                for i in range(1, self.options.clones + 1, 1):
                    last_device_slot_uid += 1
                    last_device_uid += 1
                    row.uid = last_device_slot_uid
                    row.device_id = last_device_uid
                    query = "INSERT INTO `device_slot` %s" % self.do_prep_insert(row)
                    bulk_sql.append(query)

            while bulk_sql:
                SQL.query(";".join(bulk_sql[:MAXSQL]), ifc=emsshifc)
                bulk_sql[:MAXSQL] = []

        LOG.info('Creating SelfIPs on %s...', bpmgmt)
        self_ips = [str(start_ip + ip_offset + x)
                    for x in range(1, self.options.clones + 1, 1)]
        vlan_names = ['internal'] * self.options.clones
        netmasks = ['255.255.0.0'] * self.options.clones
        unit_ids = [0] * self.options.clones
        floating_states = ['STATE_DISABLED'] * self.options.clones
        with IcontrolInterface(**self.bigipparams) as bigipicifc:
            ic = bigipicifc.api
            ic.Networking.SelfIP.create(self_ips=self_ips, vlan_names=vlan_names,
                                        netmasks=netmasks, unit_ids=unit_ids,
                                        floating_states=floating_states)
            access_lists = [dict(self_ip=x, mode='ALLOW_MODE_ALL', protocol_ports=[])
                            for x in self_ips]
            ic.Networking.SelfIPPortLockdown.add_allow_access_list(access_lists=access_lists)

    def do_delete(self):
        LOG.info('* Delete mode *')
        with SSHInterface(**self.emparams) as emsshifc:
            bpmgmt = self.bigipparams.address
            devices = SQL.query("SELECT uid,access_address FROM device WHERE mgmt_address='%s';" % bpmgmt,
                                ifc=emsshifc)
            clones = devices[1:]
            uids = [x.uid for x in clones]

        with EMInterface(**self.emicparams) as emicifc:
            emapi = emicifc.api
            LOG.info('Deleting devices...')
            try:
                emapi.device.delete_device(deviceIds=uids)
                #LOG.info('Enabling auto-refresh on EM...')
                #EMAPI.device.set_config(auto_refresh=True, ifc=emicifc)
            except ParsingError, e:
                LOG.warning(e)

        if clones:
            LOG.info('Deleting SelfIPs on %s...', bpmgmt)
            self_ips = [x.access_address for x in clones]
            with IcontrolInterface(**self.bigipparams) as bigipicifc:
                ic = bigipicifc.api
                try:
                    ic.Networking.SelfIP.delete_self_ip(self_ips=self_ips)
                except IControlFault, e:
                    LOG.warning(e)

        if devices:
            LOG.info('Reauthenticating device...')
            uid = devices[0].uid
            with EMInterface(**self.emicparams) as emicifc:
                emapi = emicifc.api
                emapi.discovery.reauthenticate(self.bigipparams.username,
                                               self.bigipparams.password, uid)

    def do_refresh(self):
        LOG.info('* Refresh mode *')
        mode = self.options.refresh
        with SSHInterface(**self.emparams) as emsshifc:
            bpmgmt = self.bigipparams.address
            if mode == 1:
                rows = SQL.query("SELECT * FROM device WHERE mgmt_address='%s' AND last_refresh IS NULL;" % bpmgmt,
                                 ifc=emsshifc)
            elif mode == 2:
                rows = SQL.query("SELECT * FROM device WHERE mgmt_address='%s' AND (last_refresh IS NULL OR refresh_failed_at IS NOT NULL);" % bpmgmt,
                                 ifc=emsshifc)
            else:
                rows = SQL.query("SELECT * FROM device WHERE mgmt_address='%s'" % bpmgmt,
                                 ifc=emsshifc)

        LOG.info("Found %d devices.", len(rows))
        with EMInterface(**self.emicparams) as emicifc:
            emapi = emicifc.api
            for row in rows:
                if not int(row.is_local_em):
                    LOG.info('Refresh %s', row.access_address)
                    try:
                        emapi.device.refresh_device(deviceIds=[row.uid])
                    except IControlTransportError, e:
                        LOG.error(e)

    def setup(self):
        if self.options.refresh:
            return self.do_refresh()
        if self.options.delete:
            return self.do_delete()
        self.do_inject()


def main():
    import optparse
    import sys

    usage = """%prog [options] <emaddress> <bigipaddress>"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2,
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="Device Cloner v%s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages")

    p.add_option("-u", "--em-root-username", metavar="USERNAME",
                 default=ROOT_USERNAME, type="string",
                 help="An user with root rights (default: %s)"
                 % ROOT_USERNAME)
    p.add_option("-p", "--em-root-password", metavar="PASSWORD",
                 default=ROOT_PASSWORD, type="string",
                 help="An user with root rights (default: %s)"
                 % ROOT_PASSWORD)
    p.add_option("", "--em-admin-username", metavar="USERNAME",
                 default=ADMIN_USERNAME, type="string",
                 help="An user with admin rights (default: %s)"
                 % ADMIN_USERNAME)
    p.add_option("", "--em-admin-password", metavar="PASSWORD",
                 default=ADMIN_PASSWORD, type="string",
                 help="An user with admin rights (default: %s)"
                 % ADMIN_PASSWORD)
    p.add_option("", "--bigip-admin-username", metavar="USERNAME",
                 default=ADMIN_USERNAME, type="string",
                 help="An user with admin rights (default: %s)"
                 % ADMIN_USERNAME)
    p.add_option("", "--bigip-admin-password", metavar="PASSWORD",
                 default=ADMIN_PASSWORD, type="string",
                 help="An user with admin rights (default: %s)"
                 % ADMIN_PASSWORD)

    p.add_option("-r", "--refresh", metavar="MODE", type="int",
                 help="Refresh mode, Refresh each device, one at a time."
                 " (1: unitialized only, 2: failed or unitialized, 3: all)")
    p.add_option("-d", "--delete", action="store_true",
                 help="Delete mode. Remove devices and self IPs.")
    p.add_option("-c", "--clones", metavar="INT",
                 default=10, type="int",
                 help="Number of clones to generate (default: 10)")
    p.add_option("-i", "--ip-offset", metavar="INT",
                 default=IPOFFSET, type="int",
                 help="The IP offset where to start adding selfIPs (default: %d)" %
                 IPOFFSET)
    p.add_option("-t", "--timeout", metavar="TIMEOUT", type="int", default=120,
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

    if len(args) < 2:
        p.print_version()
        p.print_help()
        sys.exit(2)

    cs = DeviceCloner(options=options, emaddress=args[0], bigipaddress=args[1])
    cs.run()


if __name__ == '__main__':
    main()
