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
Inc. Seattle, WA, USA. Portions created by F5 are Copyright (C) 1996-2004 F5 Networks,
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

Tested with SOAPpy 0.12.4:
    https://github.com/pelletier/SOAPpy
"""
import socket
import SOAPpy
import logging
import urllib
LOG = logging.getLogger(__name__) 

ICONTROL_URL = "https://%s:%s@%s/iControl/iControlPortal.cgi"
ICONTROL_NS = "urn:iControl"

def _dump_list(self, obj, tag, typed = 1, ns_map = {}):
    from wstools.XMLname import toXMLname
    from SOAPpy.Types  import InstanceType, structType, DictType, anyType, \
                              StringType, UnicodeType, NS, arrayType, typedArrayType
    
    tag = tag or self.gentag()
    tag = toXMLname(tag) # convert from SOAP 1.2 XML name encoding

    if type(obj) == InstanceType:
        data = obj.data
    else:
        data = obj

    if typed:
        id = self.checkref(obj, tag, ns_map)
        if id == None:
            return

    try:
        sample = data[0]
        empty = 0
    except:
        # preserve type if present
        if getattr(obj,"_typed",None) and getattr(obj,"_type",None):
            if getattr(obj, "_complexType", None):
                sample = typedArrayType(typed=obj._type,
                                        complexType = obj._complexType)
                sample._typename = obj._type
                if not getattr(obj,"_ns",None): obj._ns = NS.URN
            else:
                sample = typedArrayType(typed=obj._type)
        else:
            sample = structType()
        empty = 1

    # First scan list to see if all are the same type
    same_type = 1

    if not empty:
        for i in data[1:]:
            if type(sample) != type(i) or \
                (type(sample) == InstanceType and \
                    sample.__class__ != i.__class__):
                same_type = 0
                break

    ndecl = ''
    if same_type:
        if (isinstance(sample, structType)) or \
               type(sample) == DictType or \
               (isinstance(sample, anyType) and \
                (getattr(sample, "_complexType", None) and \
                 sample._complexType)): # force to urn struct
            try:
                tns = obj._ns or NS.URN
            except:
                tns = NS.URN

            ns, ndecl = self.genns(ns_map, tns)

            try:
                typename = sample._typename
            except:
                typename = "SOAPStruct"

            t = ns + typename
                            
        elif isinstance(sample, anyType):
            ns = sample._validNamespaceURI(self.config.typesNamespaceURI,
                                           self.config.strictNamespaces)
            if ns:
                ns, ndecl = self.genns(ns_map, ns)
                t = ns + str(sample._type)
            else:
                t = 'ur-type'
        else:
            typename = type(sample).__name__

            # For Python 2.2+
            if type(sample) == StringType: typename = 'string'

            # HACK: unicode is a SOAP string
            if type(sample) == UnicodeType: typename = 'string'
            
            # HACK: python 'float' is actually a SOAP 'double'.
            if typename=="float": typename="double"  
            t = self.genns(
            ns_map, self.config.typesNamespaceURI)[0] + typename

    else:
        t = self.genns(ns_map, self.config.typesNamespaceURI)[0] + \
            "ur-type"

    try: a = obj._marshalAttrs(ns_map, self)
    except: a = ''

    ens, edecl = self.genns(ns_map, NS.ENC)
    ins, idecl = self.genns(ns_map, self.config.schemaNamespaceURI)

    if typed:
        self.out.append(
            '<%s %sarrayType="%s[%d]" %stype="%sArray"%s%s%s%s%s%s>\n' %
            (tag, ens, t, len(data), ins, ens, ndecl, edecl, idecl,
             self.genroot(ns_map), id, a))

    if typed:
        try: elemsname = obj._elemsname
        except: elemsname = "item"
    else:
        elemsname = tag
        
    # XXX: Fix multi-dimensional arrays.
    if isinstance(data, (list, tuple, arrayType)):
        should_drill = True
    else:
        should_drill = not same_type
    
    for i in data:
        self.dump(i, elemsname, should_drill, ns_map)

    if typed: self.out.append('</%s>\n' % tag)

SOAPpy.SOAPBuilder.dump_list = _dump_list

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

    def __init__(self, hostname, username, password, timeout=90, debug=0, 
                 session=None, query=None):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.debug = debug
        self.session = session
        self.query = query
        self._parent = None
        self._cache = {}
        #LOG.debug('Icontrol new: %(username)s:%(password)s@%(hostname)s', locals())
        socket.setdefaulttimeout(timeout)

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
                url = ICONTROL_URL % (parent.username, parent.password, 
                    parent.hostname)
                ns = ICONTROL_NS + ':' + '/'.join(chain)
                if parent.query:
                    url = "%s?%s" % (url, urllib.urlencode(parent.query))
                    parent._cache.clear()

                p = parent
                if p._cache.get(ns) is not None:
                    ic = p._cache[ns]
                else:
                    if parent.session:
                        headers = SOAPpy.Types.headerType()
                        sess_t = SOAPpy.Types.integerType(parent.session)
                        sess_t._setMustUnderstand(0)
                        sess_t._setAttr('xmlns:myns1', ICONTROL_NS)
                        headers._addItem('myns1:session', sess_t)
                        ic = SOAPpy.SOAPProxy(url, ns, header=headers)
                    else:
                        ic = SOAPpy.SOAPProxy(url, ns)
                    p._cache[ns] = ic
                    ic.config.debug = p.debug
                    ic.simplify_objects = 1

                try:
                    return getattr(ic, self._name)(*args, **kw)
                except SOAPpy.Types.faultType, e:
                    if 'Unknown method' in e.faultstring:
                        raise UnknownMethod(e)
                    raise IControlFault(e)
                except SOAPpy.Errors.HTTPError, e:
                    if 401 == e.code:
                        raise AuthFailed(e)
                    raise IControlTransportError(e)

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
    print "Version is: %s\n" % version
    print "Pools:"
    for x in pools:
        print "\t%s" % x
    
if __name__ == '__main__':
    main()
