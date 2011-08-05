#!/usr/bin/env python
from M2Crypto import RSA, X509, EVP, m2, Rand
from f5test.macros.base import Macro
from f5test.interfaces.config import ConfigInterface
from f5test.interfaces.icontrol import IcontrolInterface
from f5test.interfaces.ssh import SSHInterface
from f5test.defaults import ADMIN_PASSWORD, ADMIN_USERNAME, ROOT_PASSWORD, \
                            ROOT_USERNAME, ROOTCA_STORE
from f5test.base import Options
import logging
import os
import socket
import random

LOG = logging.getLogger(__name__)

MAXINT = 4294967295
RANDPOOL_FILENAME = 'randpool.dat'
ROOTCA_PK_NAME = 'rootca.key'
ROOTCA_CRT_NAME = 'rootca.crt'

__version__ = '0.9'


class WebCert(Macro):

    # The ROOTCA path will store cert/key pair for the ROOTCA, the last serial
    # in a plain text file and the rand pool 
    def __init__(self, options, address=None):
        self.options = Options(options.__dict__)
        
        if self.options.device:
            self.address = ConfigInterface().get_device_address(options.device)
        else:
            self.address = address
        
        LOG.info('Doing: %s', self.address)
        LOG.debug('ROOTCA path is: %s', options.store)
        filename = os.path.join(self.options.store, RANDPOOL_FILENAME)
        Rand.load_file(filename, -1)
        super(WebCert, self).__init__()

    def gen_key(self, size = 1024):
        key = RSA.gen_key(size, m2.RSA_F4, lambda: None)
        pkey = EVP.PKey()
        pkey.assign_rsa(key)
        return pkey

    def load_key(self, file):
        key = RSA.load_key(file)
        pkey = EVP.PKey()
        pkey.assign_rsa(key)
        return pkey

    def load_cert(self, file):
        return X509.load_cert(file)

    def gen_request(self, pkey, cn):
        req = X509.Request()
        req.set_version(2)
        req.set_pubkey(pkey)
        name = X509.X509_Name()
        name.CN = cn
        name.Email = 'emtest@f5.com'
        name.OU = 'Enterprise Manager'
        name.O = 'F5 Networks'
        name.L = 'Seattle'
        name.ST = 'Washington'
        name.C = 'US'
        req.set_subject_name(name)

        req.sign(pkey, 'sha1')
        return req

    def gen_certificate(self, req, ca_key, ca_cert=None, aliases=None):
        
        pkey = req.get_pubkey()
        
        if not req.verify(pkey):
            # XXX: What error object should I use?
            raise ValueError, 'Error verifying request'
        
        sub = req.get_subject()
        # If this were a real certificate request, you would display
        # all the relevant data from the request and ask a human operator
        # if you were sure. Now we just create the certificate blindly based
        # on the request.
        cert = X509.X509()

        serial = random.randint(0, MAXINT)
        cert.set_serial_number(serial)
        cert.set_version(2)
        cert.set_subject(sub)
        
        if not ca_cert:
            issuer = sub
        else:
            issuer = ca_cert.get_subject()

        # Set the issuer, pubkey and not valid before/after dates
        cert.set_issuer(issuer)
        cert.set_pubkey(pkey)
        notBefore = m2.x509_get_not_before(cert.x509)
        notAfter = m2.x509_get_not_after(cert.x509)
        m2.x509_gmtime_adj(notBefore, 0)
        
        # Expires in 10 years!
        days = 365 * 10
        m2.x509_gmtime_adj(notAfter, 60 * 60 * 24 * days)

        # If aliases are specified add them as an extension
        if aliases:
            tmp = ','.join(['DNS:%s' % name for name in aliases])
            cert.add_ext(
                X509.new_extension('subjectAltName', tmp))

        # If we're creating the initial CA selfsigned cert set the CA flag
        if not ca_cert:
            ext = X509.new_extension('basicConstraints', 'critical,CA:true')
            ext.set_critical(1)
            cert.add_ext(ext)

        # Finally sign the brand new certificate
        cert.sign(ca_key, 'sha1')

        return cert

    def resolv_address(self, address):
        fqdn, _, ip_list = socket.gethostbyname_ex(address)
        return (ip_list[0], fqdn)

    def get_certificate(self):

        ip, fqdn = self.resolv_address(self.address)
        
        if ip != fqdn:
            hostname = fqdn.split('.', 1)[0]
        else:
            hostname = ip

        if self.options.alias is None:
            self.options.alias = []

        aliases = self.options.alias + list(set([ip, fqdn, hostname]))
        
        cert_pem = None
        key_pem = None
        cert_fn = os.path.join(self.options.store, 'cache', "%s.crt" % ip)
        key_fn = os.path.join(self.options.store, 'cache', "%s.key" % ip)
        
        if not self.options.force:
            if os.path.exists(cert_fn) and os.path.exists(key_fn) :
                file = open(cert_fn)
                cert_pem = file.read()
                file.close()
                file = open(key_fn)
                key_pem = file.read()
                file.close()
                LOG.debug('Using cached key/certificate pair')
        else:
            LOG.debug('Generating new key/certificate pair')

        if not cert_pem or not key_pem:
            key = self.gen_key(1024)

            cakey_fn = os.path.join(self.options.store, ROOTCA_PK_NAME)
            cacert_fn = os.path.join(self.options.store, ROOTCA_CRT_NAME)

            cakey = self.load_key(cakey_fn)
            cacert = self.load_cert(cacert_fn)

            # Have the option to use the IP as Common Name to satisfy Firefox.
            if self.options.fqdn_cn:
                req = self.gen_request(key, fqdn)
            else:
                req = self.gen_request(key, ip)
            cert = self.gen_certificate(req, cakey, cacert, aliases=aliases)
            key_pem = key.as_pem(None)
            cert_pem = cert.as_pem()
            key.save_key(key_fn, None)
            cert.save_pem(cert_fn)

            # Update the rand pool stuff
            filename = os.path.join(self.options.store, RANDPOOL_FILENAME)
            Rand.save_file(filename)

        self._cert_pem = cert_pem
        self._key_pem = key_pem

        LOG.debug(key_pem)
        LOG.debug(cert_pem)
        return (key_pem, cert_pem)

    def push_certificate(self, cert_pem_override=None, key_pem_override=None):
        
        icifc = IcontrolInterface(device=self.options.device,
                               address=self.address,
                               username=self.options.admin_username,
                               password=self.options.admin_password)
        ic = icifc.open()
        
        cert_pem = cert_pem_override or self._cert_pem
        key_pem = key_pem_override or self._key_pem
        assert cert_pem and key_pem

        try:
            ic.Management.KeyCertificate.certificate_delete(
                mode='MANAGEMENT_MODE_WEBSERVER', cert_ids=['server'])
            ic.Management.KeyCertificate.key_delete(
                mode='MANAGEMENT_MODE_WEBSERVER', key_ids=['server'])
        except:
            LOG.warning('Exception occurred while deleting cert/key')

        ic.Management.KeyCertificate.certificate_import_from_pem(
                mode='MANAGEMENT_MODE_WEBSERVER', cert_ids=['server'], 
                pem_data=[cert_pem], overwrite=1)

        ic.Management.KeyCertificate.key_import_from_pem(
                mode='MANAGEMENT_MODE_WEBSERVER', key_ids=['server'], 
                pem_data=[key_pem], overwrite=1)
        
        icifc.close()
        
        # XXX: Unfortunately we can't reinit httpd through iControl. It's a KI
        # http://devcentral.f5.com/Default.aspx?tabid=53&forumid=1&postid=1170498&view=topic
        #
        #action = pc.System.Services.typefactory.\
        #        create('System.Services.ServiceAction').\
        #        SERVICE_ACTION_REINIT
        #service = pc.System.Services.typefactory.\
        #        create('System.Services.ServiceType').\
        #        SERVICE_HTTPD
        #pc.System.Services.set_service(services = [service], \
        #                               service_action = action)
        #pc.System.Services.get_service_status([service])

        with SSHInterface(device=self.options.device,
                          address=self.address,
                          username=self.options.root_username,
                          password=self.options.root_password) as ssh:
            ssh.api.run('bigstart reinit httpd')

    def prep(self):
        LOG.info('Started...')
        self.get_certificate()
        self.push_certificate()
        LOG.info('Done.')


def main():
    import optparse
    import sys

    usage = """%prog [options] <address>"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2, 
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="Web certificate updater v%s" % __version__
        )
    p.add_option("-s", "--store", metavar="DIRECTORY",
                 default=ROOTCA_STORE, type="string",
                 help="The CA certificates store. (default: %s)" 
                 % ROOTCA_STORE)
    p.add_option("-a", "--alias", metavar="ALIAS", type="string",
                 action="append", default=[],
                 help="Aliases to put in the certificate. Can be an IP, a host "
                 "or a FQDN.")
    p.add_option("", "--verbose", action="store_true",
                 help="Debug messages")
    
    p.add_option("", "--admin-username", metavar="USERNAME",
                 default=ADMIN_USERNAME, type="string",
                 help="An user with administrator rights (default: %s)"
                 % ADMIN_USERNAME)
    p.add_option("", "--admin-password", metavar="PASSWORD",
                 default=ADMIN_PASSWORD, type="string",
                 help="An user with administrator rights (default: %s)"
                 % ADMIN_PASSWORD)
    p.add_option("", "--root-username", metavar="USERNAME",
                 default=ROOT_USERNAME, type="string",
                 help="An user with root rights (default: %s)"
                 % ROOT_USERNAME)
    p.add_option("", "--root-password", metavar="PASSWORD",
                 default=ROOT_PASSWORD, type="string",
                 help="An user with administrator rights (default: %s)"
                 % ROOT_PASSWORD)
    p.add_option("", "--fqdn-cn", action="store_true",
                 help="Set the Subject CN to the FQDN string returned by the "
                 "DNS. Otherwise the CN defaults to the IP address.")
    p.add_option("", "--force", action="store_true",
                 help="Generate a fresh key/certificate pair.")

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        logging.getLogger('paramiko.transport').setLevel(logging.ERROR)
        logging.getLogger('f5test').setLevel(logging.ERROR)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)
    
    if not args:
        p.print_version()
        p.print_help()
        sys.exit(2)
    
    cs = WebCert(options=options, address=args[0])
    cs.run()


if __name__ == '__main__':
    main()
