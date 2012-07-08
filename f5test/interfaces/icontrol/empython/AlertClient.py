from .Client import Client

class AlertClient(Client):
    def __init__(self, icontrol):
        Client.__init__(self, 'emalertd', icontrol)
