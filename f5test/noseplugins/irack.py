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
DEFAULT_RESERVATION_TIME = datetime.timedelta(hours=3)
URI_USER_NOBODY = '/api/v1/user/2/'
URI_RESERVATION = '/api/v1/reservation/'
LOG = logging.getLogger(__name__)


def datetime_to_str(date):
    date_str = date.isoformat()
    return date_str[:date_str.find('.')] # Remove microseconds

class IrackCheckout(Plugin):
    """
    iRack plugin. Enable with ``--with-irack``. This plugin checks in/out
    devices from iRack: http://go/irack
    """
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
        from f5test.interfaces.rest.irack import IrackInterface
        LOG.info("Checking out devices from iRack...")
        
        config = self.config_ifc.open()
        irackcfg = config.irack
        devices = [x for x in self.config_ifc.get_all_devices() 
                     if 'no-irack-reservation' not in x.tags]

        if not devices:
            LOG.warning('No devices to be reserved.')
            return

        address = irackcfg.get('address', DEFAULT_HOSTNAME)
        assert irackcfg.username, "Key irack.username is not set in config!"
        assert irackcfg.apikey, "Key irack.apikey is not set in config!"
        with IrackInterface(address=address,
                            timeout=irackcfg.get('timeout', DEFAULT_TIMEOUT),
                            username=irackcfg.username,
                            password=irackcfg.apikey, ssl=False) as irack:

            params = dict(q_accessaddress__in=[x.address for x in devices])
            ret = irack.api.f5asset.get(params_dict=params)
            assert ret.data.meta.total_count == len(devices), \
                "Managed devices=%d, iRack returned=%d!" % (len(devices), 
                                                            ret.data.meta.total_count)
            for asset in ret.data.objects:
                assert not asset['v_is_reserved'], \
                    "Device '%s' already has an active reservation." % \
                        self.config_ifc.get_device_by_address(asset['q_accessaddress'])

            now = datetime.datetime.now()
            now_str = datetime_to_str(now)
            end = now + DEFAULT_RESERVATION_TIME
            end_str = datetime_to_str(end)
            
            headers = {"Content-type": "application/json"}
            notes = 'runner={0}\n' \
                    'id={1}\n' \
                    'config={2}\n' \
                    'url={3}\n'.format(get_local_ip(address), 
                                     self.config_ifc.get_session().name,
                                     config._filename,
                                     self.config_ifc.get_session().get_url())
            payload = json.dumps(dict(notes=notes, 
                                      assets=[x['resource_uri'] for x in ret.data.objects],
                                      #to=URI_USER_NOBODY, # nobody
                                      start=now_str,
                                      end=end_str, 
                                      reminder='0:15:00'))
            
            ret = irack.api.from_uri(URI_RESERVATION).post(payload=payload,
                                                           headers=headers)
            LOG.debug("Checkout HTTP status: %s", ret.response.status)
            LOG.debug("Checkout location: %s", ret.response.location)
            res = urlparse(ret.response.location).path
            irackcfg._reservation = res

    def finalize(self, result):
        from f5test.interfaces.rest.irack import IrackInterface
        LOG.info("Checking in devices to iRack...")

        config = self.config_ifc.open()
        irackcfg = config.irack
        res = irackcfg._reservation

        if not res:
            LOG.warning('No devices to be un-reserved.')
            return

        with IrackInterface(address=irackcfg.get('address', DEFAULT_HOSTNAME),
                          timeout=irackcfg.get('timeout', DEFAULT_TIMEOUT),
                          username=irackcfg.username,
                          password=irackcfg.apikey, ssl=False) as irack:

            try:
                ret = irack.api.from_uri(res).delete()
                LOG.debug("Checkin HTTP status: %s", ret.response.status)
            except:
                LOG.error("Exception occured while deleting reservation")
