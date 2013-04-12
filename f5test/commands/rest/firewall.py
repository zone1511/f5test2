'''
Created on Jan 30, 2013

@author: jono
'''
from .base import RestCommand
from ..base import CommandError
from ...base import Options


create_firewall = None
class CreateFirewall(RestCommand):
    """Creates a new firewall instance on a BIGIQ.

    @rtype: dict
    """
    def __init__(self, definition, options=None, *args, **kwargs):
        super(CreateFirewall, self).__init__(*args, **kwargs)
        self.definition = definition
        self.definition.setdefault('name', 'vs_1')
        self.definition.setdefault('address', '10.11.10.1')
        self.definition.setdefault('port', 80)
        self.definition.setdefault('protocol', 'PROTOCOL_TCP')
        self.options = options or Options()

    def setup(self):
        rest = self.api
        return
