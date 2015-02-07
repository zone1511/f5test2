'''
Created on Feb 6, 2015

@author: jono
'''
from __future__ import absolute_import

import datetime
import json
import logging
from urlparse import urlparse

from . import ExtendedPlugin
from ...utils.net import get_local_ip
from ...utils.wait import wait, StopWait


# IRACK_HOSTNAME_DEBUG = '127.0.0.1:8081'
DEFAULT_TIMEOUT = 60
POLL_INTERVAL = 60
DEFAULT_HOSTNAME = 'irack.mgmt.pdsea.f5net.com'
DEFAULT_RESERVATION_TIME = datetime.timedelta(hours=4)
URI_USER_NOBODY = '/api/v1/user/2/'
URI_RESERVATION = '/api/v1/reservation/'
LOG = logging.getLogger(__name__)


def datetime_to_str(date):
    date_str = date.isoformat()
    return date_str[:date_str.find('.')]  # Remove microseconds


class IrackCheckout(ExtendedPlugin):
    """
    iRack plugin. Enable with ``--with-irack``. This plugin checks in/out
    devices from iRack: http://go/irack

    WARNING: This plugin expects an 'irack' section to be present at the ROOT
    of the test config (this is for backward compatibility).
    """
    enabled = False
    score = 530

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--with-irack', action='store_true',
                          dest='with_irack', default=False,
                          help="Enable the iRack checkin plugin. (default: no)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        from ...interfaces.config import ConfigInterface

        super(IrackCheckout, self).configure(options, noseconfig)
        self.enabled = noseconfig.options.with_irack
        self.config_ifc = ConfigInterface()
        if self.enabled:
            config = self.config_ifc.open()
            assert config.irack, "iRack checkout requested but no irack section " \
                                 "found in the config."

    def wait_on_reservation(self, irack, devices):
        params = dict(q_accessaddress__in=[x.address for x in devices])

        def loop():
            ret = irack.api.f5asset.get(params_dict=params)
            reservations = dict([(x['q_accessaddress'], x['v_is_reserved'])
                                 for x in ret.data.objects])
            not_found = set()
            reserved = set()
            for device in devices:
                if device.address not in reservations:
                    not_found.add(device)

                if reservations.get(device.address):
                    reserved.add(device)

            return not_found, reserved, ret.data.objects

        def loop_progress(x):
            if x[0]:
                raise StopWait('Devices {0[0]} were not found in iRack.'.format(x))
            elif x[1]:
                LOG.warning('Devices {0[1]} are currently reserved in iRack.'.format(x))

        return wait(loop, lambda x: not x[1], progress_cb=loop_progress,
                    interval=POLL_INTERVAL, timeout=DEFAULT_RESERVATION_TIME.seconds)[2]

    def begin(self):
        from ...interfaces.rest.irack import IrackInterface
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

            assets = self.wait_on_reservation(irack, devices)
            now = datetime.datetime.now()
            now_str = datetime_to_str(now)
            end = now + DEFAULT_RESERVATION_TIME
            end_str = datetime_to_str(end)

            headers = {"Content-type": "application/json"}
            notes = 'runner: {0}\n' \
                    'id: {1}\n' \
                    'config: {2}\n' \
                    'url: {3}\n'.format(get_local_ip(address),
                                        self.config_ifc.get_session().name,
                                        config._filename,
                                        self.config_ifc.get_session().get_url())
            payload = json.dumps(dict(notes=notes,
                                      assets=[x['resource_uri'] for x in assets],
                                      # to=URI_USER_NOBODY, # nobody
                                      start=now_str,
                                      end=end_str,
                                      reminder='0:15:00'))

            ret = irack.api.from_uri(URI_RESERVATION).post(payload=payload,
                                                           headers=headers)
            LOG.debug("Checkout HTTP status: %s", ret.response.status)
            LOG.debug("Checkout location: %s", ret.response.location)
            res = urlparse(ret.response.location).path
            irackcfg._reservation = res
