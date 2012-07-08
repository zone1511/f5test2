from .Client import Client

class FileClient(Client):
    def __init__(self, icontrol):
        Client.__init__(self, 'emfiled', icontrol)
