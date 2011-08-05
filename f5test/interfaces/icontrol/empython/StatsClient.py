from .Client import Client

class StatsClient(Client):
    def __init__(self, icontrol):
        Client.__init__(self, 'emstatsd', icontrol)
