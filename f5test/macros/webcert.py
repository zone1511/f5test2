#!/usr/bin/env python
from OpenSSL import crypto
from f5test.macros.base import Macro
from f5test.interfaces.config import ConfigInterface
from f5test.interfaces.icontrol import IcontrolInterface
from f5test.interfaces.ssh import SSHInterface
from f5test.defaults import ADMIN_PASSWORD, ADMIN_USERNAME, ROOT_PASSWORD, \
                            ROOT_USERNAME
from f5test.base import Options
from f5test.utils.wait import wait
import logging
import os
import socket
import sys
import random

__version__ = '1.0'
LOG = logging.getLogger(__name__)

F5TEST_SUBJECT = Options(CN='NotSet',
                         emailAddress='emtest@f5.com',
                         OU='Enterprise Manager',
                         O='F5 Networks',
                         L='Seattle',
                         ST='Washington',
                         C='US'
)

MAXINT = 4294967295
DEFAULT_TIMEOUT = 300

# Subject: CN=F5 EM Testing/emailAddress=emtest@f5.com, OU=Enterprise Manager, O=F5 Networks, L=Seattle, ST=Washington, C=US
# Validity
#    Not Before: Mar  5 02:22:01 2010 GMT
#    Not After : Mar  2 02:22:01 2020 GMT

ROOTCA_CRT = """-----BEGIN CERTIFICATE-----
MIICxTCCAi6gAwIBAgIBATANBgkqhkiG9w0BAQUFADCBnTEWMBQGA1UEAxMNRjUg
RU0gVGVzdGluZzEcMBoGCSqGSIb3DQEJARYNZW10ZXN0QGY1LmNvbTEbMBkGA1UE
CxMSRW50ZXJwcmlzZSBNYW5hZ2VyMRQwEgYDVQQKEwtGNSBOZXR3b3JrczEQMA4G
A1UEBxMHU2VhdHRsZTETMBEGA1UECBMKV2FzaGluZ3RvbjELMAkGA1UEBhMCVVMw
HhcNMTAwMzA1MDIyMjAxWhcNMjAwMzAyMDIyMjAxWjCBnTEWMBQGA1UEAxMNRjUg
RU0gVGVzdGluZzEcMBoGCSqGSIb3DQEJARYNZW10ZXN0QGY1LmNvbTEbMBkGA1UE
CxMSRW50ZXJwcmlzZSBNYW5hZ2VyMRQwEgYDVQQKEwtGNSBOZXR3b3JrczEQMA4G
A1UEBxMHU2VhdHRsZTETMBEGA1UECBMKV2FzaGluZ3RvbjELMAkGA1UEBhMCVVMw
gZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBALzE7nq8L8hL2M+1lCE2MNpyVSZw
YFK93n/EtWyz5NeZNtNWTDDtQCx18nPBqn7G+pQnm16t12MP3qr8LBanrBIbZcb6
I6/jc37al3zMsLx+Eht4Wy2kJWmh7eOUgPH/7pbasvTXywhYgBllOlkALUXiDKdi
BOF9EnkzfLShIosnAgMBAAGjEzARMA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcN
AQEFBQADgYEAeg/a/RP7UoOcQ0X65C2WHgPM37aKQs/dIfCZuQ0WqNSFy94Uan3u
mpZI2dBUGF66+AjsMsu1+XteBTXkY25eJdOq9N1R0dwQFMT9HVBMv1RxzLKPB1SJ
8AR0KI04X6oWaWnEpnNA/6OOy90QwbsqsRB3mHzLUe4jJtqVjaRk8P4=
-----END CERTIFICATE-----"""

ROOTCA_KEY = """-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBALzE7nq8L8hL2M+1
lCE2MNpyVSZwYFK93n/EtWyz5NeZNtNWTDDtQCx18nPBqn7G+pQnm16t12MP3qr8
LBanrBIbZcb6I6/jc37al3zMsLx+Eht4Wy2kJWmh7eOUgPH/7pbasvTXywhYgBll
OlkALUXiDKdiBOF9EnkzfLShIosnAgMBAAECgYBwhshOe73UHXqKHwjFX4NxxLQD
rPuOd0aaTY2E1hv1dYzcIFZc2CDoIAs+e9UBq+WVyaJxpxl9IOmwbZBulNcaEgmN
V0ILsk/CRUwgbvdMqAm8e2j4JSDk5EcE05d3J27AFNcvE1zYr+18mxXZjZREAF7Z
wuzlNsHjZo8epLGt6QJBAN0U1DpBc546Oaks1lMvrfkMVfPRxK2A96rTfKbF4oRL
9HFFM6NtobPsnhsy66SF69vWtns315NLKk9tGHGpX/0CQQDalZmUZYJFqOaW2HHp
5MsibrLoHF+jWv6EHvZQYcKNn5w1fuXCYO0RxYWtoRgBIJoI6wIkwPesH0XEMOq4
9obzAkAz3n8sa87EgMSmfG6MddNLayl/WufaDTgOTDAisKrEf02KhcHnxgD6RbmS
iA/hOcpseaO2pRNe63Oxzta9VA/BAkEAkqEGPEj34bjSrmAV0lvbdIaj1xaphVCW
KZUHkJZzx0NJq40rnYAdp+1DplzJWIBBNDhJ4NPdkQYNa/WQj3E4xwJAV08tiAuu
uLfuCyGJZ0FkPX2ixMRiXerlDM1INo+AsU9nU6smWwKY8wqspxqf6Zo6D7+pdZKX
z8hiS4Tqr8Pqlw==
-----END PRIVATE KEY-----"""


if sys.version_info < (3, 0):
    def b(s):
        return s
    bytes = str #@ReservedAssignment
else:
    def b(s):
        return s.encode("charmap")
    bytes = bytes #@ReservedAssignment


class WebCert(Macro):
    def __init__(self, options, address=None):
        self.options = Options(options.__dict__)
        
        self.address = ConfigInterface().get_device_address(options.device) \
                       if self.options.device else address

        if self.options.alias is None:
            self.options.alias = []

        super(WebCert, self).__init__()

    @staticmethod
    def create_key_pair(ktype, bits):
        """
        Create a public/private key pair.
    
        Arguments: type - Key type, must be one of TYPE_RSA and TYPE_DSA
                   bits - Number of bits to use in the key
        Returns:   The public/private key pair in a PKey object
        """
        pkey = crypto.PKey()
        pkey.generate_key(ktype, bits)
        return pkey
    
    @staticmethod
    def create_cert_request(pkey, digest="md5", **name):
        """
        Create a certificate request.
    
        Arguments: pkey   - The key to associate with the request
                   digest - Digestion method to use for signing, default is md5
                   **name - The name of the subject of the request, possible
                            arguments are:
                              C     - Country name
                              ST    - State or province name
                              L     - Locality name
                              O     - Organization name
                              OU    - Organizational unit name
                              CN    - Common name
                              emailAddress - E-mail address
        Returns:   The certificate request in an X509Req object
        """
        req = crypto.X509Req()
        subj = req.get_subject()
    
        for (key,value) in name.items():
            setattr(subj, key, value)
    
        req.set_pubkey(pkey)
        req.sign(pkey, digest)
        return req
    
    @staticmethod
    def create_certificate(req, (issuer_key, issuer_cert), serial, 
                           (not_before, not_after), digest="sha1", extensions=None):
        """
        Generate a certificate given a certificate request.
    
        Arguments: req        - Certificate reqeust to use
                   issuerCert - The certificate of the issuer
                   issuerKey  - The private key of the issuer
                   serial     - Serial number for the certificate
                   notBefore  - Timestamp (relative to now) when the certificate
                                starts being valid
                   notAfter   - Timestamp (relative to now) when the certificate
                                stops being valid
                   digest     - Digest method to use for signing, default is md5
        Returns:   The signed certificate in an X509 object
        """
        cert = crypto.X509()
        cert.set_version(2)
        cert.set_serial_number(serial)
        cert.gmtime_adj_notBefore(not_before)
        cert.gmtime_adj_notAfter(not_after)
        cert.set_issuer(issuer_cert.get_subject())
        cert.set_subject(req.get_subject())
        cert.set_pubkey(req.get_pubkey())
        if extensions:
            cert.add_extensions(extensions)
        cert.sign(issuer_key, digest)
        return cert

    def gen_certificate(self, cn, alt_names=None):
        assert cn
        # Load ROOTCA certificate and private key.
        if self.options.ca_crt and self.options.ca_key:
            crt = open(os.path.join(self.options.ca_crt))
            key = open(os.path.join(self.options.ca_key))
            capair = (
                crypto.load_privatekey(crypto.FILETYPE_PEM, key.read()),
                crypto.load_certificate(crypto.FILETYPE_PEM, crt.read()))
            crt.close()
            key.close()
        else:
            capair = (
                crypto.load_privatekey(crypto.FILETYPE_PEM, ROOTCA_KEY),
                crypto.load_certificate(crypto.FILETYPE_PEM, ROOTCA_CRT))
        
        pkey = WebCert.create_key_pair(crypto.TYPE_RSA, 1024)
        subject = F5TEST_SUBJECT
        subject.CN = cn
        req = WebCert.create_cert_request(pkey, **subject)

        serial = random.randint(0, MAXINT)
        
        extensions = []
        if alt_names:
            tmp = ','.join(['DNS:%s' % name for name in alt_names])
            extensions.append(crypto.X509Extension(b('subjectAltName'), False, b(tmp)))
        
        # Stick some nifty extensions- just for fun.
        extensions.append(crypto.X509Extension(b('basicConstraints'), False, 
                                               b('CA:FALSE')))
        extensions.append(crypto.X509Extension(b('keyUsage'), False, 
                                               b('digitalSignature,keyEncipherment')))
        extensions.append(crypto.X509Extension(b('extendedKeyUsage'), False, 
                                               b('serverAuth,clientAuth')))
        extensions.append(crypto.X509Extension(b('authorityInfoAccess'), False, 
                                               b('caIssuers;email:emtest@f5.com')))
        extensions.append(crypto.X509Extension(b('crlDistributionPoints'), False, 
                                               b('URI:http://172.27.58.1/rootca.crl')))

        return (pkey, WebCert.create_certificate(req, capair, serial,
                                                 (-60*60*24*1, 60*60*24*365*10),  # -1 .. 10 years
                                                 extensions=extensions))

    def push_certificate(self, pkey, cert):
        
        icifc = IcontrolInterface(device=self.options.device,
                                  address=self.address,
                                  username=self.options.admin_username,
                                  password=self.options.admin_password,
                                  port=self.options.ssl_port,
                                  debug=self.options.verbose)
        ic = icifc.open()
        key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)
        cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        
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
                          password=self.options.root_password,
                          port=self.options.ssh_port) as ssh:
            ssh.api.run('bigstart reinit httpd')
        
        return True

    def setup(self):
        LOG.info('WebCert started...')
        fqdn, _, ip_list = socket.gethostbyname_ex(self.address)
        aliases = set([x for x in self.options.alias + ip_list + [fqdn]])
        pkey, cert = self.gen_certificate(self.address, alt_names=aliases)
        
        # Sometimes it fails due to voodoo race conditions. That's why we wait()!
        wait(lambda: self.push_certificate(pkey, cert), 
             timeout=self.options.timeout)
        LOG.info('Done.')


def main():
    import optparse

    usage = """%prog [options] <address>"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2, 
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="Web certificate updater v%s" % __version__
        )
    p.add_option("", "--ca-key", metavar="FILE",
                 type="string", help="The CA private key file in PEM format. "
                 "(default: embedded)")
    p.add_option("", "--ca-crt", metavar="FILE",
                 type="string", help="The CA certificate file in PEM format. "
                 "(default: embedded)")
    p.add_option("-a", "--alias", metavar="ALIAS", type="string",
                 action="append", default=[],
                 help="Additional hostnames or IP addresses to put in the "
                 "subjectAltName certificate extension.")
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages.")
    
    p.add_option("", "--ssl-port", metavar="INTEGER", type="int", default=443,
                 help="SSL Port. (default: 443)")
    p.add_option("", "--ssh-port", metavar="INTEGER", type="int", default=22,
                 help="SSH Port. (default: 22)")
    p.add_option("", "--admin-username", metavar="USERNAME",
                 default=ADMIN_USERNAME, type="string",
                 help="(default: %s)"
                 % ADMIN_USERNAME)
    p.add_option("", "--admin-password", metavar="PASSWORD",
                 default=ADMIN_PASSWORD, type="string",
                 help="(default: %s)"
                 % ADMIN_PASSWORD)
    p.add_option("", "--root-username", metavar="USERNAME",
                 default=ROOT_USERNAME, type="string",
                 help="(default: %s)"
                 % ROOT_USERNAME)
    p.add_option("", "--root-password", metavar="PASSWORD",
                 default=ROOT_PASSWORD, type="string",
                 help="(default: %s)"
                 % ROOT_PASSWORD)
    p.add_option("", "--timeout",
                 default=DEFAULT_TIMEOUT, type="int",
                 help="The SSH timeout. (default: %d)" % DEFAULT_TIMEOUT)

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
