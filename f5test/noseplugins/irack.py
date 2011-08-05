'''
Created on Jun 16, 2011

@author: jono
'''
from __future__ import absolute_import
from nose.plugins.base import Plugin
import logging
import datetime
import json
#import time
from urlparse import urlparse
from ..utils.net import get_local_ip

#IRACK_HOSTNAME_DEBUG = '127.0.0.1:8081'
DEFAULT_TIMEOUT = 60
DEFAULT_HOSTNAME = 'irack.mgmt.pdsea.f5net.com'
DEFAULT_RESERVATION_TIME = datetime.timedelta(hours=2)
URI_USER_NOBODY = '/api/v1/user/2/'
URI_RESERVATION = '/api/v1/reservation/'
LOG = logging.getLogger(__name__)


def datetime_to_str(date):
    date_str = date.isoformat()
    return date_str[:date_str.find('.')] # Remove microseconds

class IrackCheckout(Plugin):
    enabled = False
    name = "irack"
    score = 530

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--with-irack', action='store_true',
                          dest='with_irack', default=False,
                          help="Enable the iRack checkin plugin. (default: no)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        from f5test.interfaces.config import ConfigInterface

        Plugin.configure(self, options, noseconfig)
        self.options = options
        if options.with_irack:
            self.enabled = True
        self.config_ifc = ConfigInterface()
        if self.enabled:
            config = self.config_ifc.open()
            assert config.irack, "iRack checkout requested but no irack section " \
                                 "found in the config."

    def begin(self):
        from f5test.interfaces.irack import IrackInterface
        LOG.info("Checking out devices from iRack...")
        
        config = self.config_ifc.open()
        irackcfg = config.irack
        devices = list(self.config_ifc.get_all_devices())
        assert devices, "No managed devices?"

        address = irackcfg.get('address', DEFAULT_HOSTNAME)
        with IrackInterface(address=address,
                          timeout=irackcfg.get('timeout', DEFAULT_TIMEOUT),
                          username=irackcfg.username,
                          password=irackcfg.apikey) as irack:

            params = dict(q_accessaddress__in=[x.address for x in devices])
            ret = irack.api.f5asset.get(params_dict=params)
            assert ret['meta']['total_count'] == len(devices), \
                "Managed devices=%d, iRack returned=%d!" % (len(devices), 
                                                            ret['meta']['total_count'])
            for asset in ret['objects']:
                assert not asset['v_is_reserved'], \
                    "Device '%s' already has an active reservation." % \
                        self.config_ifc.get_device_by_address(asset['q_accessaddress'])

            now = datetime.datetime.now()
            now_str = datetime_to_str(now)
            end = now + DEFAULT_RESERVATION_TIME
            end_str = datetime_to_str(end)
            
            headers = {"Content-type": "application/json"}
            payload = json.dumps(dict(notes='By TestRunner @ %s' % get_local_ip(address), 
                                      assets=[x['resource_uri'] for x in ret['objects']],
                                      to=URI_USER_NOBODY, # nobody
                                      start=now_str,
                                      end=end_str, 
                                      reminder='0:15:00'))
            res = URI_RESERVATION
            ret = irack.api.resource().resource.post(res, payload=payload,
                                                    headers=headers)
            LOG.debug("Checkout HTTP status: %s", ret.status)
            LOG.debug("Checkout location: %s", ret.location)
            res = urlparse(ret.location).path
            irackcfg._reservation = res

    def finalize(self, result):
        from f5test.interfaces.irack import IrackInterface
        LOG.info("Checking in devices to iRack...")

#        time.sleep(5)
        config = self.config_ifc.open()
        irackcfg = config.irack
        res = irackcfg._reservation
        assert res, "irack._reservation key not found?"

        with IrackInterface(address=irackcfg.get('address', DEFAULT_HOSTNAME),
                          timeout=irackcfg.get('timeout', DEFAULT_TIMEOUT),
                          username=irackcfg.username,
                          password=irackcfg.apikey) as irack:

            try:
                ret = irack.api.resource().resource.delete(res)
                LOG.debug("Checkin HTTP status: %s", ret.status)
            except:
                LOG.error("Exception occured while deleting reservation")
