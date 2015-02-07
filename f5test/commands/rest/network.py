'''
Created on Oct 16, 2014

@author: jono
'''
from .base import IcontrolRestCommand
from ...interfaces.rest.emapi.objects import NetworkSelfip, NetworkVlan
from netaddr import IPNetwork
from ...utils.dicts import inverse
from ...base import Options, AttrDict
from ...interfaces.rest.emapi.objects.system import EasySetup
import logging

LOG = logging.getLogger(__name__)


get_self_ips = None
class GetSelfIps(IcontrolRestCommand):  # @IgnorePep8
    """Get self IPs for every VLAN and also add an extra IP version property ."""

    def __init__(self, *args, **kwargs):
        super(GetSelfIps, self).__init__(*args, **kwargs)

    def setup(self):
        vlans = {x.selfLink: x for x in self.ifc.api.get(path=NetworkVlan.URI)['items']}
        resp = self.ifc.api.get(path=NetworkSelfip.URI)['items']
        for item in resp:
            if item.vlanReference:
                item.vlanReference = vlans[item.vlanReference.link]
            # item.version = IPNetwork(item.address).version

        return Options(inverse({IPNetwork(x.address): x.vlanReference.name for x in resp}))

change_ntps = None
class ChangeNtps(IcontrolRestCommand):  # @IgnorePep8
    """Patch NTP servers in easyconfig
    @param ntps: list of ntp servers
    @type ntps: list of strings

    """

    def __init__(self, ntps=None, *args, **kwargs):
        super(ChangeNtps, self).__init__(*args, **kwargs)

        if ntps is None:
            ntps = ["ntp.f5net.com"]
        elif type(ntps) is not list:
            ntps = [ntps]
        self.ntps = ntps

    def setup(self):

        resp = self.ifc.api.get(EasySetup.URI)
        # print json.dumps(resp, sort_keys=True, indent=4, ensure_ascii=False)
        if resp.ntpServerAddresses != self.ntps:
            LOG.info("Patching NTPs servers to {0}...".format(self.ntps))
            self.ifc.api.patch(EasySetup.URI, AttrDict(ntpServerAddresses=self.ntps))
