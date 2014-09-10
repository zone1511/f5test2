'''
Created on Jan 6, 2014

@author: jono
'''
import logging
import time

from netaddr import IPAddress
from pysnmp.carrier.asynsock.dgram import udp, udp6
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto.api import v2c

from threading import Thread
from ...utils.net import get_local_ip
from ...utils.wait import wait

# from pysnmp.carrier.asynsock.dispatch import AsynsockDispatcher
# from pyasn1.codec.ber import decoder
# from pysnmp.proto import api
LOG = logging.getLogger(__name__)
TIMEOUT = 90
DEFAULT_JOB = 1


class TrapListener(Thread):

    def __init__(self, engine):
        super(TrapListener, self).__init__()
        self.engine = engine

    def run(self):
        self.engine.transportDispatcher.jobStarted(DEFAULT_JOB)

        try:
            self.engine.transportDispatcher.runDispatcher()
        finally:
            self.engine.transportDispatcher.closeDispatcher()
            self.engine = None


class SNMPWrapException(Exception):
    pass


class SNMPWrap(object):

    def __init__(self, host, port=161, timeout=1, version=2, community='public',
                 username='', auth=None, priv=None,
                 auth_protocol=cmdgen.usmNoAuthProtocol,
                 priv_protocol=cmdgen.usmNoPrivProtocol,
                 security_name=None):
        self.host = unicode(host)
        self.version = version
        self.transport = cmdgen.UdpTransportTarget((host, port),
                                                   timeout=timeout)

        # SNMP v1
        if version == 1:
            self.auth = cmdgen.CommunityData('public', mpModel=0)
        # SNMP v2c
        elif version == 2:
            self.auth = cmdgen.CommunityData('test-agent', community)
        # SNMP v3 SHA+AES128
        elif version == 3:
            assert username, 'username was not specified'
            self.auth = cmdgen.UsmUserData(username, auth, priv,
                                           authProtocol=auth_protocol,
                                           privProtocol=priv_protocol,
                                           securityName=security_name)
        else:
            raise ValueError('Only v1, v2c and v3 supported')

    def _err_check(self, ret, returns_table=False):
        errorIndication, errorStatus, errorIndex, values = ret
        if errorIndication:
            raise SNMPWrapException(errorIndication)
        else:
            if errorStatus:
                if returns_table:
                    message = values[-1][int(errorIndex) - 1]
                else:
                    message = values[int(errorIndex) - 1]
                # LOG.error('%s at %s' % (errorStatus.prettyPrint(), message))
                raise SNMPWrapException('%s at %s' % (errorStatus.prettyPrint(),
                                                      message))

        return values

    @staticmethod
    def _format_oids(args):
        oids = []
        for oid in args:
            if isinstance(oid, basestring):
                oid = map(lambda x: int(x), filter(None, oid.split('.')))
            oids.append(oid)
        return oids

    def get(self, *args):
        oids = SNMPWrap._format_oids(args)
        ret = cmdgen.CommandGenerator().getCmd(self.auth, self.transport,
                                               *oids)

        return self._err_check(ret)

    def getnext(self, *args):
        oids = SNMPWrap._format_oids(args)
        ret = cmdgen.CommandGenerator().nextCmd(self.auth, self.transport,
                                                *oids)

        return self._err_check(ret, returns_table=True)

    def getbulk(self, n, r, *args):
        oids = SNMPWrap._format_oids(args)
        ret = cmdgen.CommandGenerator().bulkCmd(self.auth, self.transport,
                                                n, r, *oids)

        return self._err_check(ret, returns_table=True)

    def set(self, *args):
        oids = SNMPWrap._format_oids(args)
        ret = cmdgen.CommandGenerator().setCmd(self.auth, self.transport,
                                               *oids)

        return self._err_check(ret)

    def start_listener(self, callback, address=None, port=1162, community='public',
                       timeout=TIMEOUT):
        '''
        Start a TRAP v1/v2c/v3 notification receiver with predefined users.

        @param callback: Takes these args snmpEngine, stateReference,
                         contextEngineId, contextName, varBinds, cbCtx
        @param address: The address to listen to
        @param port: The port to listen to
        @param community: The community name for v2c

        Predefined users:
        usr-md5-des
        usr-md5-none
        usr-sha-aes128

        Auth: authkey1
        Priv: privkey1
        '''
        if not address:
            address = get_local_ip(self.host)
        if timeout < 0:
            timeout = 10 ** 10
        # Create SNMP engine with auto-generated engineID and pre-bound
        # to socket transport dispatcher
        snmpEngine = engine.SnmpEngine()

        # Transport setup
        if IPAddress(address).version == 4:
            # UDP over IPv4
            domain_oid = udp.domainName
            transport = udp.UdpTransport()
        else:
            # UDP over IPv6
            domain_oid = udp6.domainName
            transport = udp6.Udp6Transport()

        # Waiting up to TIMEOUT seconds for the port to be released
        LOG.debug('Waiting for port %s:%d to become available...', address, port)
        transport = wait(lambda: transport.openServerMode((address, port)),
                         timeout=TIMEOUT, interval=1)
        LOG.info('Listening for traps on %s:%d...', address, port)

        config.addSocketTransport(snmpEngine, domain_oid, transport)

        # Terrible monkey patching!!
        # But there's no other way to cause the dispatcher loop to end if we
        # don't get what we expect in a given amount of time. For now that time
        # is limited to TIMEOUT seconds.
        end = time.time() + timeout

        def jobsArePending(self):
            if self._AbstractTransportDispatcher__jobs and time.time() < end:
                return 1
            else:
                return 0
        snmpEngine.transportDispatcher.__class__.jobsArePending = jobsArePending

        # SNMPv1/2 setup
        config.addV1System(snmpEngine, 'test-agent', community)

        # SNMPv3/USM setup
        # user: usr-md5-des, auth: MD5, priv DES
        config.addV3User(
            snmpEngine, 'usr-md5-des',
            config.usmHMACMD5AuthProtocol, 'authkey1',
            config.usmDESPrivProtocol, 'privkey1'
        )

        # user: usr-md5-des, auth: MD5, priv DES, contextEngineId: 8000000001020304
        # this USM entry is used for TRAP receiving purposes
        config.addV3User(
            snmpEngine, 'usr-md5-des',
            config.usmHMACMD5AuthProtocol, 'authkey1',
            config.usmDESPrivProtocol, 'privkey1',
            contextEngineId=v2c.OctetString(hexValue='8000000001020304')
        )

        # user: usr-md5-none, auth: MD5, priv NONE
        config.addV3User(
            snmpEngine, 'usr-md5-none',
            config.usmHMACMD5AuthProtocol, 'authkey1'
        )

        # user: usr-md5-none, auth: MD5, priv NONE, contextEngineId: 8000000001020304
        # this USM entry is used for TRAP receiving purposes
        config.addV3User(
            snmpEngine, 'usr-md5-none',
            config.usmHMACMD5AuthProtocol, 'authkey1',
            contextEngineId=v2c.OctetString(hexValue='8000000001020304')
        )

        # user: usr-sha-aes128, auth: SHA, priv AES
        config.addV3User(
            snmpEngine, 'usr-sha-aes128',
            config.usmHMACSHAAuthProtocol, 'authkey1',
            config.usmAesCfb128Protocol, 'privkey1'
        )
        # user: usr-sha-aes128, auth: SHA, priv AES, contextEngineId: 8000000001020304
        # this USM entry is used for TRAP receiving purposes
        config.addV3User(
            snmpEngine, 'usr-sha-aes128',
            config.usmHMACSHAAuthProtocol, 'authkey1',
            config.usmAesCfb128Protocol, 'privkey1',
            contextEngineId=v2c.OctetString(hexValue='8000000001020304')
        )

#         def sample_callback(snmpEngine, stateReference, contextEngineId, contextName,
#                             varBinds, cbCtx):
#             print('Notification received, ContextEngineId "%s", ContextName "%s"' % (
#                   contextEngineId.prettyPrint(), contextName.prettyPrint())
#             )
#             for name, val in varBinds:
#                 print('%s = %s' % (name.prettyPrint(), val.prettyPrint()))
#             print

        # If callback() returns True we'll stop the loop
        def callback_wrapper(*args, **kwargs):
            if callback(*args, **kwargs):
                snmpEngine.transportDispatcher.jobFinished(DEFAULT_JOB)

        # Register SNMP Application at the SNMP engine
        ntfrcv.NotificationReceiver(snmpEngine, callback_wrapper)

        #return address, port
        t = TrapListener(snmpEngine)
        t.start()
        return address, port, t
