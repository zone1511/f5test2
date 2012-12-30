'''
Created on Feb 22, 2012

@author: jono
'''
from restkit import Resource
from ...base import AttrDict
from ...utils.querydict import QueryDict
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = False


class WrappedResponse(object):

    def __init__(self, response):
        self.response = response
        self.body = response.body_string()
        self._data = None

    @staticmethod
    def _parse_json(data):
        if not json:
            return data
        return json.loads(data)

    @staticmethod
    def _parse(mimetype, data):
        common_indent = {
            'application/json': WrappedResponse._parse_json,
        }
        if mimetype in common_indent:
            return common_indent[mimetype](data)
        return data

    @property
    def data(self):
        if self._data:
            return self._data

        ctype = self.response.headers['Content-Type']
        try:
            mimetype, _ = ctype.split(";")
        except ValueError:
            mimetype = ctype.split(";")[0]

        # indent body
        body = self.body
        if body:
            self._data = AttrDict(WrappedResponse._parse(mimetype, body))
            return self._data
        return AttrDict()


class RestResource(Resource):
    trailing_slash = False

    @staticmethod
    def _parse_json(data):
        if not json:
            return data
        return json.dumps(data)

    @staticmethod
    def _parse(mimetype, data):
        common_indent = {
            'application/json': RestResource._parse_json,
        }
        if mimetype in common_indent:
            return common_indent[mimetype](data)
        return data

    def request(self, method, path=None, payload=None, headers=None,
                params_dict=None, **params):

        if path is not None:
            path = str(path)
            bits = path.split('?', 1)
            if len(bits) > 1:
                path = bits[0]
                query_dict = QueryDict(bits[1])
                if not params_dict:
                    params_dict = {}
                params_dict.update(query_dict)

            if self.trailing_slash and path[-1] != '/':
                path += '/'

        if payload and headers.get('Content-Type'):
            ctype = headers['Content-Type']
            try:
                mimetype, _ = ctype.split(";")
            except ValueError:
                mimetype = ctype.split(";")[0]

            payload = RestResource._parse(mimetype, payload)

        response = super(RestResource, self).request(method, path=path,
                                                     payload=payload,
                                                     headers=headers,
                                                     params_dict=params_dict,
                                                     **params)
        return WrappedResponse(response)

    def get_by_id(self, *args):
        slash = '/' if self.trailing_slash else ''
        if len(args) == 1:
            return self.get('{0[0]}{1}'.format(args, slash))
        return self.get('set/{0}{1}'.format(';'.join([str(x) for x in args]),
                                            slash))

    def filter(self, **kwargs):  # @ReservedAssignment
        return self.get(params_dict=kwargs)
