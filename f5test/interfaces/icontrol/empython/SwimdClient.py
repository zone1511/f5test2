from .Client import Client

class SwimdClient(Client):
    def __init__(self, icontrol):
        Client.__init__(self, 'swimd', icontrol)
