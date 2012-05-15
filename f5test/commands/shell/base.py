from .. import base
from ...interfaces.ssh import SSHInterface


class CommandNotSupported(Exception):
    pass

class SSHCommandError(Exception):
    pass


class SSHCommand(base.Command):
    """Base class for SSH commands. It makes sure the SSH transport is 
    connected before running the command.
    
    If an already opened SSH interface is provided (through the interface 
    param) the cleanup method will leave it open. This is useful when a SSH 
    channel is reused to run a batch of commands.
    
    @param interface: L{SSHInterface} instance. Doesn't need to be connected.
    @type interface: SSHInterface
    @param device: a device alias from the configuration file
    @type interface: str
    @param address: an IP address or hostname 
    @type address: str
    @param username: the username used to authenticate the SSH connection
    @type username: str
    @param password: the password used to authenticate the SSH connection
    @type password: str
    """
    def __init__(self, ifc=None, device=None, address=None, username=None, 
                 password=None, port=22, timeout=180, *args, **kwargs):
        if ifc is None:
            self.ifc = SSHInterface(device, address, username, password, 
                                    port=port, timeout=timeout)
            self._keep_alive = False
        else:
            self.ifc = ifc
            self._keep_alive = True

        super(SSHCommand, self).__init__(*args, **kwargs)

    def __repr__(self):
        parent = super(SSHCommand, self).__repr__()
        opt = {}
        opt['address'] = self.ifc.address
        opt['username'] = self.ifc.username
        opt['password'] = self.ifc.password
        opt['port'] = self.ifc.port
        return parent + "(address=%(address)s port=%(port)s username=%(username)s " \
                        "password=%(password)s)" % opt

    def prep(self):
        if not self.ifc.is_opened():
            self.ifc.open()
        self.api = self.ifc.api

    def cleanup(self):
        if not self._keep_alive:
            self.ifc.close()

