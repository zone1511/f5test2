#!/bin/env python

"""
----------------------------------------------------------------------------
The contents of this file are subject to the "END USER LICENSE AGREEMENT FOR F5
Software Development Kit for iControl"; you may not use this file except in
compliance with the License. The License is included in the iControl
Software Development Kit.

Software distributed under the License is distributed on an "AS IS"
basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See
the License for the specific language governing rights and limitations
under the License.

The Original Code is iControl Code and related documentation
distributed by F5.

The Initial Developer of the Original Code is F5 Networks,
Inc. Seattle, WA, USA. Portions created by F5 are Copyright (C) 1996-2004, 2011 F5 Networks,
Inc. All Rights Reserved.  iControl (TM) is a registered trademark of F5 Networks, Inc.

Alternatively, the contents of this file may be used under the terms
of the GNU General Public License (the "GPL"), in which case the
provisions of GPL are applicable instead of those above.  If you wish
to allow use of your version of this file only under the terms of the
GPL and not to allow others to use your version of this file under the
License, indicate your decision by deleting the provisions above and
replace them with the notice and other provisions required by the GPL.
If you do not delete the provisions above, a recipient may use your
version of this file under either the License or the GPL.

Pycontrol, version 3. Written by Ionut Turturica for F5 Networks, Inc.

Tested with SOAPpy 0.12.5:
    https://github.com/pelletier/SOAPpy
"""
import socket
import SOAPpy
import logging
import urllib
LOG = logging.getLogger(__name__) 

ICONTROL_URL = "%(proto)s://%(username)s:%(password)s@%(hostname)s:%(port)s/iControl/iControlPortal.cgi"
ICONTROL_NS = "urn:iControl"


class IControlFault(Exception):
    def __init__(self, *args, **kwargs):
        e = args[0]
        self.faultcode = e.faultcode
        self.faultstring = e.faultstring
        super(IControlFault, self).__init__(*args, **kwargs)

class UnknownMethod(IControlFault):
    pass

class IControlTransportError(Exception):
    def __init__(self, *args, **kwargs):
        e = args[0]
        self.faultcode = e.code
        self.faultstring = e.msg
        super(IControlTransportError, self).__init__(*args, **kwargs)

class AuthFailed(IControlTransportError):
    pass

class Icontrol(object):
    """
    Yet another SOAPpy wrapper for iControl aware devices.
    
    >>> from pycontrol3 import Icontrol
    >>> ic = Icontrol('172.27.58.103', 'admin', 'admin', debug=0)
    >>> print ic.System.Cluster.get_member_ha_state(cluster_names=['default'], slot_ids=[[1,2,3,4]])
    [['HA_STATE_ACTIVE', 'HA_STATE_ACTIVE', 'HA_STATE_ACTIVE', 'HA_STATE_ACTIVE']]
    >>> 

    """

    def __init__(self, hostname, username, password, port=443, timeout=90,
                 debug=0, proto='https', session=None):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.proto = proto
        self.timeout = timeout
        self._debug = debug
        self._session = session
        self._url_params = None
        self._icontrol_url = ICONTROL_URL
        self._icontrol_ns = ICONTROL_NS
        self._parent = None
        self._cache = {}

    class __Method(object):
        
        def __init__(self, name, parent=None):
            self._name = name
            self._parent = parent

        def __call__(self, *args, **kw):
            if self._name == "_":
                if self.__name in ["__repr__","__str__"]:
                    return self.__repr__()
            else:
                chain = []
                parent = self._parent
                while parent._parent:
                    chain = [parent._name] + chain
                    parent = parent._parent
                url = parent._icontrol_url % parent.__dict__
                ns = parent._icontrol_ns + ':' + '/'.join(chain)
                if parent._url_params:
                    url = "%s?%s" % (url, urllib.urlencode(parent._url_params))
                    parent._cache.clear()

                p = parent
                if p._cache.get(ns) is not None:
                    ic = p._cache[ns]
                else:
                    if parent._session:
                        headers = SOAPpy.Types.headerType()
                        sess_t = SOAPpy.Types.integerType(parent._session)
                        sess_t._setMustUnderstand(0)
                        sess_t._setAttr('xmlns:myns1', parent._icontrol_ns)
                        headers._addItem('myns1:session', sess_t)
                        ic = SOAPpy.SOAPProxy(url, ns, header=headers, 
                                              timeout=p.timeout)
                    else:
                        ic = SOAPpy.SOAPProxy(url, ns, timeout=p.timeout)
                    p._cache[ns] = ic
                    ic.config.debug = p._debug
                    ic.simplify_objects = 1

                try:
                    # An ugly way of setting the timeout per socket, but it
                    # seems that SOAPpy is ignoring the timeout parameter set in
                    # the SOAPProxy constructor.
                    before = socket.getdefaulttimeout()
                    socket.setdefaulttimeout(p.timeout)
                    return getattr(ic, self._name)(*args, **kw)
                except SOAPpy.Types.faultType, e:
                    if 'Unknown method' in e.faultstring:
                        raise UnknownMethod(e)
                    raise IControlFault(e)
                except SOAPpy.Errors.HTTPError, e:
                    if 401 == e.code:
                        raise AuthFailed(e)
                    raise IControlTransportError(e)
                finally:
                    socket.setdefaulttimeout(before)

        def __repr__(self):
            return "<%s>" % self._name

        def __getattr__(self, name):
            if name == '__del__':
                raise AttributeError, name
            if name[0] != "_":
                return self.__class__(name, self)

    def __getattr__(self, name):
        if name in ( '__del__', '__getinitargs__', '__getnewargs__',
           '__getstate__', '__setstate__', '__reduce__', '__reduce_ex__'):
            raise AttributeError, name
        return self.__Method(name, self)

def main():
    import sys
    if len(sys.argv) < 4:
        print "Usage: %s <hostname> <username> <password>"% sys.argv[0]
        sys.exit()

    a = sys.argv[1:]
    b = Icontrol(
            hostname = a[0],
            username = a[1],
            password = a[2])

    pools = b.LocalLB.Pool.get_list()
    version = b.LocalLB.Pool.get_version()
    print "Version: %s\n" % version
    print "Pools:"
    for x in pools:
        print "\t%s" % x
    
if __name__ == '__main__':
    main()
