from .Client import Client

class AdminClient(Client):
    def __init__(self, icontrol):
        Client.__init__(self, 'emadmind', icontrol)
