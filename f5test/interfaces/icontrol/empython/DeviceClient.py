from .Client import Client

class DeviceClient(Client):
    def __init__(self, icontrol):
        Client.__init__(self, 'emdeviced', icontrol)
