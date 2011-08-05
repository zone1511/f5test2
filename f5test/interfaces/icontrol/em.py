'''
An EMPython port as an interface.

Created on Apr 21, 2011

@author: jono
'''
from ..config import ConfigInterface, DeviceAccess
#from .driver import Icontrol
from .core import IcontrolInterface
from ...base import Interface
from ...defaults import ADMIN_USERNAME, ADMIN_PASSWORD


class EmApi(object):
    
    def __init__(self, icontrol):
        self.icontrol = icontrol
    
    @property
    def device(self):
        from .empython.api.DeviceAPI import DeviceAPI
        return DeviceAPI(self.icontrol)

    @property
    def discovery(self):
        from .empython.api.DiscoveryAPI import DiscoveryAPI
        return DiscoveryAPI(self.icontrol)

    @property
    def file(self):
        from .empython.api.FileAPI import FileAPI
        return FileAPI(self.icontrol)

    @property
    def legacy_software_install(self):
        from .empython.api.LegacySoftwareInstallAPI import LegacySoftwareInstallAPI
        return LegacySoftwareInstallAPI(self.icontrol)

    @property
    def software_install(self):
        from .empython.api.SoftwareInstallAPI import SoftwareInstallAPI
        return SoftwareInstallAPI(self.icontrol)

    @property
    def enabledisable(self):
        from .empython.api.EnableDisableAPI import EnableDisableAPI
        return EnableDisableAPI(self.icontrol)

    @property
    def big3d_install(self):
        from .empython.api.Big3dInstallAPI import Big3dInstallAPI
        return Big3dInstallAPI(self.icontrol)

    @property
    def stats(self):
        from .empython.api.StatsAPI import StatsAPI
        return StatsAPI(self.icontrol)


class EMInterface(Interface):
    
    def __init__(self, device=None, icifc=None, address=None, 
                 username=ADMIN_USERNAME, password=ADMIN_PASSWORD, 
                 timeout=180, *args, **kwargs):
        super(EMInterface, self).__init__()

        self.icifc = icifc
        if device or not address:
            self.device = device if isinstance(device, DeviceAccess) \
                        else ConfigInterface().get_device(device)
        else:
            self.device = device
        self.address = address
        self.username = username
        self.password = password
        self.timeout = timeout

    def __str__(self):
        if isinstance(self.device, DeviceAccess):
            return self.device.address
        return self.address or 'em-icontrol'

    @property
    def version(self):
        from ...commands.icontrol.system import get_version
        return get_version(ifc=self.icifc)

    def open(self):
        if self.api:
            return self.api
        if self.device or not self.address:
            device = self.device
            address = device.address
            username = device.get_admin_creds().username
            password = device.get_admin_creds().password
            self.device = device.get_alias()
            self.address = address
            self.username = username
            self.password = password
        else:
            address = self.address
            username = self.username
            password = self.password

        if not self.icifc:
            self.icifc = IcontrolInterface(address=address, 
                                              username=username, 
                                              password=password, 
                                              timeout=self.timeout)
            self.icifc.open()
        self.api = EmApi(self.icifc.api)
        return self.api
