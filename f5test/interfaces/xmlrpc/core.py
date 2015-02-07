"""
Example:

    with BugzillaInterface('http://mgmtdata.mgmt.pdsea.f5net.com/xmlrpc.cgi',
                           'i.turturica@f5.com', 'f5site02', debug=0) as bzifc:
        print bzifc.api.Bug.search(dict(id=493024))
"""

from .driver import XmlRpc
from ...base import Interface


class BugzillaInterface(Interface):

    def __init__(self, address, username=None, password=None,
                 timeout=90, debug=0, *args, **kwargs):
        super(BugzillaInterface, self).__init__()

        self.address = address
        self.username = username
        self.password = password
        self.timeout = timeout
        self.debug = debug
        self.user_id = None
        self.token = None

    def open(self):  # @ReservedAssignment
        if self.api is not None:
            return self.api

        self.api = XmlRpc(self.address, timeout=self.timeout, verbose=self.debug)

        if self.username and self.password:
            # Login, get a cookie into our cookie jar:
            ret = self.api.User.login(dict(login=self.username,
                                           password=self.password))
            # Record the user ID in case the script wants this
            self.user_id = ret['id']
            self.token = ret.get('token')

        return self.api
