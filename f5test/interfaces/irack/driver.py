'''
Created on May 16, 2011

@author: jono
'''
from restkit import Resource
from urlparse import urljoin
from ...utils.querydict import QueryDict
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = False


def indent_json(data):
    if not json:
        return data
    return json.loads(data)

common_indent = {
    'application/json': indent_json,
}

def indent(mimetype, data):
    if mimetype in common_indent:
        return common_indent[mimetype](data)
    return data

def prettify(response):
    ctype = response.headers['Content-Type']
    try:
        mimetype, encoding = ctype.split(";")
    except ValueError:
        mimetype = ctype.split(";")[0]
        
    # indent body
    return indent(mimetype, response.body_string())


class Irack(object):
    
    def __init__(self, address, username, password, timeout=180):
        url = "http://%s:%s@%s" % (username, password, address)
        self.url = url
        self.timeout = timeout
        self.asset = IrackResource(url, '/api/v1/asset/', timeout=timeout)
        self.f5asset = IrackResource(url, '/api/v1/f5asset/', timeout=timeout)
        self.user = IrackResource(url, '/api/v1/user/', timeout=timeout)
        self.reservation = IrackResource(url, '/api/v1/reservation/', timeout=timeout)
        self.staticbag = IrackResource(url, '/api/v1/staticbag/', timeout=timeout)
        self.staticaddress = IrackResource(url, '/api/v1/staticaddress/', timeout=timeout)
        self.staticlicense = IrackResource(url, '/api/v1/staticlicense/', timeout=timeout)
        self.staticcredential = IrackResource(url, '/api/v1/staticcredential/', timeout=timeout)
        self.staticsystem = IrackResource(url, '/api/v1/staticsystem/', timeout=timeout)

    def resource(self, path=None):
        return IrackResource(self.url, path, timeout=self.timeout)


class IrackResource(object):

    def __init__(self, url, path, *args, **kwargs):
        self.url = url
        self.resource = Resource(uri=url, *args, **kwargs)
        self.path = path

    def get(self, path='', params_dict=None):
        path = urljoin(self.path, path)
        bits = path.split('?', 1)
        if len(bits) > 1:
            path = bits[0]
            params_dict = QueryDict(bits[1])
        return prettify(self.resource.get(path, params_dict=params_dict))
    
    def get_by_id(self, *args):
        if len(args) == 1:
            return self.get('%d/' % args[0])
        return self.get('set/%s/' % ';'.join([str(x) for x in args]))

    def filter(self, **kwargs):
        return self.get(params_dict=kwargs)
