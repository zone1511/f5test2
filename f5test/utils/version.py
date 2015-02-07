#!/bin/env python
import re


class InvalidVersionString(Exception):
    """Raised when invalid version strings are used.
    """


class IllegalComparison(Exception):
    """Raised when invalid version strings are used.
    """


def py2x_cmp(a, b):
    return (a > b) - (a < b)


class Product(object):
    """Normalized product."""
    EM = 'em'
    BIGIP = 'bigip'
    WANJET = 'wanjet'
    ARX = 'arx'
    SAM = 'sam'
    BIGIQ = 'bigiq'
    NSX = 'nsx'

    def __init__(self, product_string):
        """String to Product class converter.

        >>> Product('EM 1.2')
        em
        >>> Product('Enterprise Manager')
        em
        >>> Product('BIG-IP_v9.3.1')
        bigip
        >>> Product('BIGIP')
        bigip
        """
        if re.search("(?:EM|Enterprise Manager)", str(product_string), re.IGNORECASE):
            self.product = Product.EM
        elif re.search("BIG-?IP", str(product_string), re.IGNORECASE):
            self.product = Product.BIGIP
        elif re.search("BIG-?IQ", str(product_string), re.IGNORECASE):
            self.product = Product.BIGIQ
        elif re.search("(?:WANJET|WJ)", str(product_string), re.IGNORECASE):
            self.product = Product.WANJET
        elif re.search("ARX", str(product_string), re.IGNORECASE):
            self.product = Product.ARX
        elif re.search("BIG-IP_SAM", str(product_string), re.IGNORECASE):
            self.product = Product.SAM
        elif re.search("NSX", str(product_string), re.IGNORECASE):
            self.product = Product.NSX
        else:
            self.product = ''

    @property
    def is_bigip(self):
        return self.product == Product.BIGIP

    @property
    def is_bigiq(self):
        return self.product == Product.BIGIQ

    @property
    def is_em(self):
        return self.product == Product.EM

    @property
    def is_wanjet(self):
        return self.product == Product.WANJET

    @property
    def is_sam(self):
        return self.product == Product.SAM

    @property
    def is_none(self):
        return self.product == ''

    @property
    def to_tmos(self):
        if self.product == Product.EM:
            return 'EM'
        elif self.product == Product.BIGIP:
            return 'BIG-IP'
        elif self.product == Product.BIGIQ:
            return 'BIG-IQ'
        else:
            return str(self).upper()

    def __cmp__(self, other):
        if not isinstance(other, Product):
            other = Product(other)

        return py2x_cmp(self.product, other.product)

    def __repr__(self):
        return self.product

    def __int__(self):
        return [Product.EM,
                Product.BIGIP,
                Product.BIGIQ,
                Product.WANJET,
                Product.ARX,
                Product.SAM].index(self.product)

    __hash__ = __int__


class Version(object):
    """Generic Version + Build object.
    Samples:

    >>> Version('1.1')
    <Version: 1.1.0 0.0.0>
    >>> Version('9.3.1')
    <Version: 9.3.1 0.0.0>
    >>> Version('9.3.1 650.0')
    <Version: 9.3.1 650.0.0>
    >>> Version('11.0.1 build6901.45.4')
    <Version: 11.0.1 6901.45.4>
    >>> Version('11.0.1') > '9.3.0'
    True
    >>> Version('9.3.1') > '9.3.1 1.0'
    False
    >>> Version('bigip 9.3.1') > 'em 1.8'
    False
    >>> Version('bigip 9.3.1') < 'em 1.8'
    False

    etc..
    """
    def __init__(self, version=None, product=None):

        if isinstance(version, Version):
            self.pmajor = version.pmajor
            self.pminor = version.pminor
            self.ppatch = version.ppatch
            self.bnum = version.bnum
            self.bhotfix = version.bhotfix
            self.bdevel = version.bdevel
            self.product = version.product
        else:
            mo = re.search("(\d+)\.(\d+)\.?(\d+)?[^\d]*(\d+)?\.?(\d+)?\.?(\d+)?",
                          str(version), re.IGNORECASE)

            if mo is None:
                (self.pmajor, self.pminor, self.ppatch,
                 self.bnum, self.bhotfix, self.bdevel) = (0, 0, 0, 0, 0, 0)
            else:
                (self.pmajor, self.pminor, self.ppatch,
                 self.bnum, self.bhotfix, self.bdevel) = map(lambda x: int(x or 0),
                                                            mo.groups())

#            self.version = "%s.%s.%s" % (self.pmajor, self.pminor, self.ppatch)
#
#            if self.bdevel:
#                self.build = "%s.%s.%s" % (self.bnum, self.bhotfix, self.bdevel)
#            else:
#                self.build = "%s.%s" % (self.bnum, self.bhotfix)

            if product:
                self.product = Product(product)
            else:
                self.product = Product(version)

    def __abs__(self):
        tmp = Version(self)
        tmp.bnum = 0
        tmp.bhotfix = 0
        tmp.bdevel = 0
        return tmp

    def __eq__(self, other):
        result = self._cmp(other)
        if result is None:
            return False
        else:
            return result == 0

    def __ne__(self, other):
        result = self._cmp(other)
        if result is None:
            return False
        else:
            return result != 0

    def __lt__(self, other):
        result = self._cmp(other)
        if result is None:
            return False
        else:
            return result < 0

    def __le__(self, other):
        result = self._cmp(other)
        if result is None:
            return False
        else:
            return result <= 0

    def __gt__(self, other):
        result = self._cmp(other)
        if result is None:
            return False
        else:
            return result > 0

    def __ge__(self, other):
        result = self._cmp(other)
        if result is None:
            return False
        else:
            return result >= 0

    def __nonzero__(self):
        return not self.is_none

    def _cmp(self, other):
        """Easy comparsion with like-objects or other strings"""

        if not isinstance(other, Version):
            other = Version(other)

        if (self.product is None and not other.product is None) or \
           (not self.product is None and other.product is None):
            raise IllegalComparison("Product is missing from one of the versions.")

        if self.product != other.product:
            return None

        return py2x_cmp(self.pmajor, other.pmajor) or \
               py2x_cmp(self.pminor, other.pminor) or \
               py2x_cmp(self.ppatch, other.ppatch) or \
               py2x_cmp(self.bnum, other.bnum) or \
               py2x_cmp(self.bhotfix, other.bhotfix) or \
               py2x_cmp(self.bdevel, other.bdevel)

    @property
    def is_none(self):
        return self == '0.0.0'

    @property
    def version(self):
        if self.is_none:
            return ''
        return "%(pmajor)d.%(pminor)d.%(ppatch)d" % self.__dict__

    @property
    def build(self):
        if self.is_none:
            return ''

        if self.bdevel:
            return "%(bnum)d.%(bhotfix)d.%(bdevel)d" % self.__dict__
        else:
            return "%(bnum)d.%(bhotfix)d" % self.__dict__

    def __repr__(self):
        if self.is_none:
            return '<Version: None>'

        if self.bdevel:
            if self.product.is_none:
                return "<Version: %(pmajor)d.%(pminor)d.%(ppatch)d " \
                       "%(bnum)d.%(bhotfix)d.%(bdevel)d>" % self.__dict__
            return "<Version: %(product)s %(pmajor)d.%(pminor)d.%(ppatch)d " \
                   "%(bnum)d.%(bhotfix)d.%(bdevel)d>" % self.__dict__

        if self.product.is_none:
            return "<Version: %(pmajor)d.%(pminor)d.%(ppatch)d " \
                   "%(bnum)d.%(bhotfix)d>" % self.__dict__
        return "<Version: %(product)s %(pmajor)d.%(pminor)d.%(ppatch)d " \
               "%(bnum)d.%(bhotfix)d>" % self.__dict__

    def __str__(self):
        if self.is_none:
            return ''
        bits = []
        if self.product:
            bits.append(self.product.to_tmos)
        bits.append(self.version)
        bits.append(self.build)
        return ' '.join(bits)

    def __int__(self):
        return self.pmajor * 10 ** 5 + \
               self.pminor * 10 ** 4 + \
               self.ppatch * 10 ** 3 + \
               self.bnum * 10 ** 2 + \
               self.bhotfix * 10 ** 1 + \
               self.bdevel * 10 ** 0 + \
               int(self.product) * 10 ** 6

    __hash__ = __int__

if __name__ == '__main__':

    assert not Version("10.1.1") < '9.4.8'
    assert not Version("9.4.8 1.0") < Version('9.4.8')
    assert Version("9.4.8 1.0") < '9.4.8 3.0'
    assert not Version("11.0.0 6900.0") <= '10.2.1 397.0.1'
    print 'Cool!'
