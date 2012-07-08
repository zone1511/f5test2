from ..DeviceClient import DeviceClient
from ..MessageParser import Dictionary, Array, String

class DiscoveryAPI(DeviceClient):

    def discoverByAddress(self, discUsername, discPassword, discoverySpecs):
        """discoverySpecs is a list of dictionaries each with keys 'address',
        username, and password"""
         
        req = Dictionary()
        req.put('discUsername', String(discUsername))
        req.put('discPassword', String(discPassword))
        discoverySpecsArray = Array()
        for spec in discoverySpecs:
            d = Dictionary()
            for key in spec.keys():
                d.put(key, String(spec[key]))
            discoverySpecsArray.add(d)
        req.put('discoverySpecs', discoverySpecsArray)
        return self.sendMsg('discoverByAddress', req)

    def discoverByCidr(self, ip, mask, discUsername, discPassword):
        req = Dictionary()
        req.put('ip', String(ip))
        req.put('mask', String(mask))
        req.put('discUsername', String(discUsername))
        req.put('discPassword', String(discPassword))
        return self.sendMsg('discoverByCidr', req)

    def discover_cancel(self, job_uid):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        return self.sendMsg('discover_cancel', req)

    def reauthenticate(self, form_username, password, deviceUid):
        req = Dictionary()
        req.put('form_username', String(form_username))
        req.put('password', String(password))
        req.put('deviceUid', String(deviceUid))
        self.sendMsg('reauthenticate', req)

