'''
Created on Dec 15, 2011

@author: jono
'''
from .base import IcontrolCommand
from ..base import  WaitableCommand, CommandError

import logging
LOG = logging.getLogger(__name__)
NAME_PATTERN = "{0.folder}/test_rd_{0.id}"


create_route_domain = None
class CreateRouteDomain(WaitableCommand, IcontrolCommand):
    """Create a new Route Domain.
    Supported: 10.1.0+

    @param id: The route domain ID.
    @type id: long
    @rtype: str
    """

    def __init__(self, id, folder='/Common', *args, **kwargs):  # @ReservedAssignment
        super(CreateRouteDomain, self).__init__(*args, **kwargs)
        self.id = id
        self.folder = folder

    def setup(self):
        ic = self.api
        v = self.ifc.version

        if v >= 'bigip 11.0.0':
            name = NAME_PATTERN.format(self)
            ic.Networking.RouteDomainV2.create(route_domains=[name],
                                               ids=[self.id],
                                               vlans=[[]])
        elif v >= 'bigip 10.1.0':
            ic.Networking.RouteDomain.create(route_domains=[self.id],
                                             vlans=[[]])
        else:
            raise CommandError("Unsupported version: %s" % v)


delete_route_domain = None
class DeleteRouteDomain(WaitableCommand, IcontrolCommand):
    """Delete a Route Domain.
    Supported: 10.1.0+

    @param id: The route domain ID
    @type id: long
    @rtype: str
    """

    def __init__(self, id, folder='/Common', *args, **kwargs):  # @ReservedAssignment
        super(DeleteRouteDomain, self).__init__(*args, **kwargs)
        self.id = id
        self.folder = folder

    def setup(self):
        ic = self.api
        v = self.ifc.version

        if v >= 'bigip 11.0.0':
            name = NAME_PATTERN.format(self)
            ic.Networking.RouteDomainV2.delete_route_domain(route_domains=[name])
        elif v >= 'bigip 10.1.0':
            ic.Networking.RouteDomain.delete_route_domain(route_domains=[self.id])
        else:
            raise CommandError("Unsupported version: %s" % v)
