'''
Created on Apr 25, 2011

@author: jono
'''
from ...base import Command
from ....interfaces.icontrol import EMInterface
import logging

LOG = logging.getLogger(__name__) 

class EMCommand(Command):
    """Base class for Icontrol Commands. If api argument is provided it will
    reuse the opened interface otherwise it will open/close a new interface
    using the address, username and password parameters. 
    
    @param device: a device alias from config
    @type device: str
    @param ifc: an opened EMInterface interface
    @type ifc: EMInterface
    @param icontrol: an opened underlying icontrol interface. This is going to
                     be used to open the EMInterface.
    @type icontrol: Icontrol
    @param address: IP address or hostname
    @type address: str
    @param username: the admin username
    @type username: str
    @param password: the admin password
    @type password: str
    """
    def __init__(self, device=None, ifc=None, icontrol=None,
                address=None, username=None, password=None, timeout=90,
                *args, **kwargs):
        super(EMCommand, self).__init__(*args, **kwargs)
        
        self.ifc = ifc
        if self.ifc is None:
            self.ifc = EMInterface(device, icontrol, address, username, 
                                   password, timeout)
            self.api = self.ifc.open()
            self._keep_alive = False
        else:
            assert isinstance(self.ifc, EMInterface), 'Interface provided is not an IcontrolInterface'
            assert self.ifc.is_opened(), 'The interface must be pre-opened'
            self.api = self.ifc.api
            self._keep_alive = True

    def prep(self):
        pass

    def cleanup(self):
        if not self._keep_alive:
            self.ifc.close()
