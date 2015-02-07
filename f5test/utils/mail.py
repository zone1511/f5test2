'''
Created on Jan 21, 2014

@author: jono
'''
from __future__ import absolute_import
import asynchat
import asyncore
import base64
import logging
import smtpd
import socket
import ssl
import tempfile
import time

from threading import Thread
from .wait import wait
from .net import get_local_ip

TIMEOUT = 90
LOG = logging.getLogger(__name__)
MGMT_HOST = 'f5.com'
SSL_KEY = """-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAMtk7Hfc393gllfT
klDLoZTG+XGgt9WEYa20x11QwIieaGV7+RY7TXCETKqpaW6mB7yTJbL0WpBwHnGX
uP+SodDOUFGwyH5vycfvbpI9RQUsrNGoFTmMRwslmwxBQ908LNUhS9Cnn1deGdHJ
VVgSublnp4aB4rHU0YAYN/ikIM5bAgMBAAECgYBlo8N/ioLcr9SxgurFMV1Hqb8R
h00WiBb/5S0Tdr0gCHkG7dLlxzDFn3doeUxUnOeU1ruqF+4B6+VqwnUSUkZF3Ab6
hz5f7IUwfuSYgYEJ/hBrx7eQ0zisitmsX9H6s9/xK7+owF+Omh441HgTUTAwIuDH
Wl8q8hK4PFmkmTpE8QJBAOuGJxHhKJmNA8y3Ui4LN48emGL+0MBJ6qk1DvgbWoZy
7YVXNWw7ozgS5Sm1hQG0wD79gkSOOtu8/Vop2EwrFY0CQQDdE6/ZMbn2hxSN3CJy
3LmIhnB8k4VObHidvj8/cnAPZTmcGvegUUebacihLjuFLkxSOggHj9yw5we6neKp
i3WHAkEA5GTehF8lIOp3kdEAV3g3M4nG2tEiHCZR8i5qyryz54eRv+mW+9NFb34b
TnwhdEsU1sC9z79hYm99/C5x+0MYjQJBANgBvlW3En5gKaMaLcaRB+7vfMUb1qpz
rb5i/qVdiURhoVJ3vu+zuwWM7G0gISPVwtisvt+0nutyMMkULz19d80CQBmNlqH3
myq1r8SGgosZzbFMlxMPOrWSzAjWSbI5BeFouEd6jH3KV/J5/MDLvaAL7CFVlVXP
biiXixiiQNEKf7Y=
-----END PRIVATE KEY-----"""

SSL_CRT = """-----BEGIN CERTIFICATE-----
MIIDQTCCAqqgAwIBAgIEMncsgTANBgkqhkiG9w0BAQUFADCBnTEWMBQGA1UEAxMN
RjUgRU0gVGVzdGluZzEcMBoGCSqGSIb3DQEJARYNZW10ZXN0QGY1LmNvbTEbMBkG
A1UECxMSRW50ZXJwcmlzZSBNYW5hZ2VyMRQwEgYDVQQKEwtGNSBOZXR3b3JrczEQ
MA4GA1UEBxMHU2VhdHRsZTETMBEGA1UECBMKV2FzaGluZ3RvbjELMAkGA1UEBhMC
VVMwHhcNMTQwMTIyMjMwNDIzWhcNMjQwMTIxMjMwNDIzWjCBkzELMAkGA1UEBhMC
VVMxDDAKBgNVBAMTA2FzZDEQMA4GA1UEBxMHU2VhdHRsZTEUMBIGA1UEChMLRjUg
TmV0d29ya3MxEzARBgNVBAgTCldhc2hpbmd0b24xHDAaBgkqhkiG9w0BCQEWDWVt
dGVzdEBmNS5jb20xGzAZBgNVBAsTEkVudGVycHJpc2UgTWFuYWdlcjCBnzANBgkq
hkiG9w0BAQEFAAOBjQAwgYkCgYEAy2Tsd9zf3eCWV9OSUMuhlMb5caC31YRhrbTH
XVDAiJ5oZXv5FjtNcIRMqqlpbqYHvJMlsvRakHAecZe4/5Kh0M5QUbDIfm/Jx+9u
kj1FBSys0agVOYxHCyWbDEFD3Tws1SFL0KefV14Z0clVWBK5uWenhoHisdTRgBg3
+KQgzlsCAwEAAaOBlTCBkjAJBgNVHRMEAjAAMAsGA1UdDwQEAwIFoDAdBgNVHSUE
FjAUBggrBgEFBQcDAQYIKwYBBQUHAwIwKQYIKwYBBQUHAQEEHTAbMBkGCCsGAQUF
BzACgQ1lbXRlc3RAZjUuY29tMC4GA1UdHwQnMCUwI6AhoB+GHWh0dHA6Ly8xNzIu
MjcuNTguMS9yb290Y2EuY3JsMA0GCSqGSIb3DQEBBQUAA4GBAFoztqGwtOiBbG4p
zYKMOHh//Gz7Q4YMWlO42Y7D3NOdMuqUuc81lGE4kdB5TemO86PB+OO431IEeuV1
KChv0dMmJAKrUCrstUlvCC9ktVhT54vx4uDkeGCBipPdngxh8fBxmlqaqM9XcwjB
2TluY5nVHkVWTZobNKFiD5xiCqcv
-----END CERTIFICATE-----"""

SSL_ROOTCA = """-----BEGIN CERTIFICATE-----
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


class MailListener(Thread):

    def __init__(self, server, timeout, ntf=None):
        super(MailListener, self).__init__(name='MailListener')
        self.server = server
        self.timeout = timeout if timeout > 0 else 10 ** 10
        self.ntf = ntf

    def run(self):
        #asyncore.loop(timeout=30, count=10)
        #asyncore.loop()
        end = time.time() + self.timeout
        while time.time() < end and self.server.accepting:
            asyncore.loop(timeout=1, count=1)
        self.server.close()
        if self.ntf:
            self.ntf.close()
            self.ntf.unlink(self.ntf.name)


class CredentialValidator(object):
    def __init__(self, credentials):
        self.credentials = [] if credentials is None else credentials

    def validate(self, username, password):
        for c_username, c_password in self.credentials:
            if username == c_username and password == c_password:
                LOG.info('User %s authenticated', username)
                return True
        return False


class AuthSMTPChannel(asynchat.async_chat):
    COMMAND = 0
    DATA = 1

    def __init__(self, server, conn, addr):
        asynchat.async_chat.__init__(self, conn)
        self.__server = server
        self.__conn = conn
        self.__addr = addr
        self.__line = []
        self.__state = self.COMMAND
        self.__greeting = 0
        self.__mailfrom = None
        self.__rcpttos = []
        self.__data = ''
        self.__fqdn = socket.getfqdn()
        try:
            self.__peer = conn.getpeername()
        except socket.error, err:
            # a race condition  may occur if the other end is closing
            # before we can get the peername
            self.close()
            if err[0] != smtpd.errno.ENOTCONN:
                raise
            return
        LOG.debug('Peer: %s', repr(self.__peer))
        self.push('220 %s %s' % (self.__fqdn, smtpd.__version__))
        self.set_terminator('\r\n')

        self.require_authentication = server.require_authentication
        self.authenticating = False
        self.authenticated = False
        self.username = None
        self.password = None
        self.credential_validator = server.credential_validator
        if server.tls:
            self.smtp_STARTTLS = self._smtp_STARTTLS
        #self.debug = True

    # Overrides base class for convenience
    def push(self, msg):
        if self.debug:
            LOG.info(msg)
        asynchat.async_chat.push(self, msg + '\r\n')

    def close_when_done(self):
        asynchat.async_chat.close_when_done(self)
        if self.__server.shutdown:
            self.__server.close()

    # Implementation of base class abstract method
    def collect_incoming_data(self, data):
        self.__line.append(data)

    def found_terminator(self):
        line = smtpd.EMPTYSTRING.join(self.__line)

        if self.debug:
            LOG.info(line)

        self.__line = []
        if self.__state == self.COMMAND:
            if not line:
                self.push('500 Error: bad syntax')
                return
            method = None
            i = line.find(' ')

            if self.authenticating:
                # If we are in an authenticating state, call the
                # method smtp_AUTH.
                arg = line.strip()
                command = 'AUTH'
            elif i < 0:
                command = line.upper()
                arg = None
            else:
                command = line[:i].upper()
                arg = line[i + 1:].strip()

            # White list of operations that are allowed prior to AUTH.
            if not command in ['AUTH', 'EHLO', 'HELO', 'NOOP', 'RSET', 'QUIT',
                               'STARTTLS']:
                if self.require_authentication and not self.authenticated:
                    self.push('530 Authentication required')

            method = getattr(self, 'smtp_' + command, None)
            if not method:
                self.push('502 Error: command "%s" not implemented' % command)
                return
            method(arg)
            return
        else:
            if self.__state != self.DATA:
                self.push('451 Internal confusion')
                return
            # Remove extraneous carriage returns and de-transparency according
            # to RFC 821, Section 4.5.2.
            data = []
            for text in line.split('\r\n'):
                if text and text[0] == '.':
                    data.append(text[1:])
                else:
                    data.append(text)
            self.__data = smtpd.NEWLINE.join(data)
            status = self.__server.process_message(
                self.__peer,
                self.__mailfrom,
                self.__rcpttos,
                self.__data
            )
            self.__rcpttos = []
            self.__mailfrom = None
            self.__state = self.COMMAND
            self.set_terminator('\r\n')
            if not status:
                self.push('250 Ok')
            else:
                self.push(status)

    # SMTP and ESMTP commands
    def smtp_HELO(self, arg):
        if not arg:
            self.push('501 Syntax: HELO hostname')
            return
        if self.__greeting:
            self.push('503 Duplicate HELO/EHLO')
        else:
            self.__greeting = arg
            self.push('250 %s' % self.__fqdn)

    def smtp_NOOP(self, arg):
        if arg:
            self.push('501 Syntax: NOOP')
        else:
            self.push('250 Ok')

    def smtp_QUIT(self, arg):
        # args is ignored
        self.push('221 Bye')
        self.close_when_done()

    # factored
    def __getaddr(self, keyword, arg):
        address = None
        keylen = len(keyword)
        if arg[:keylen].upper() == keyword:
            address = arg[keylen:].strip()
            if not address:
                pass
            elif address[0] == '<' and address[-1] == '>' and address != '<>':
                # Addresses can be in the form <person@dom.com> but watch out
                # for null address, e.g. <>
                address = address[1:-1]
        return address

    def smtp_MAIL(self, arg):
        LOG.debug('===> MAIL %s', arg)
        address = self.__getaddr('FROM:', arg) if arg else None
        if not address:
            self.push('501 Syntax: MAIL FROM:<address>')
            return
        if self.__mailfrom:
            self.push('503 Error: nested MAIL command')
            return
        self.__mailfrom = address
        LOG.debug('sender: %s', self.__mailfrom)
        self.push('250 Ok')

    def smtp_RCPT(self, arg):
        LOG.debug('===> RCPT %s', arg)
        if not self.__mailfrom:
            self.push('503 Error: need MAIL command')
            return
        address = self.__getaddr('TO:', arg) if arg else None
        if not address:
            self.push('501 Syntax: RCPT TO: <address>')
            return
        self.__rcpttos.append(address)
        LOG.debug('recips: %s', self.__rcpttos)
        self.push('250 Ok')

    def smtp_RSET(self, arg):
        if arg:
            self.push('501 Syntax: RSET')
            return
        # Resets the sender, recipients, and data, but not the greeting
        self.__mailfrom = None
        self.__rcpttos = []
        self.__data = ''
        self.__state = self.COMMAND
        self.push('250 Ok')

    def smtp_DATA(self, arg):
        if not self.__rcpttos:
            self.push('503 Error: need RCPT command')
            return
        if arg:
            self.push('501 Syntax: DATA')
            return
        self.__state = self.DATA
        self.set_terminator('\r\n.\r\n')
        self.push('354 End data with <CR><LF>.<CR><LF>')

    def smtp_EHLO(self, arg):
        if not arg:
            self.push('501 Syntax: HELO hostname')
            return
        if self.__greeting:
            self.push('503 Duplicate HELO/EHLO')
        else:
            self.push('250-%s Hello %s' % (self.__fqdn, arg))
            self.push('250-AUTH LOGIN')
            if self.__server.tls:
                self.push('250-STARTTLS')
            self.push('250 EHLO')

    def smtp_AUTH(self, arg):
        if 'LOGIN' in arg:
            self.authenticating = True
            split_args = arg.split(' ')

            # Some implmentations of 'LOGIN' seem to provide the username
            # along with the 'LOGIN' stanza, hence both situations are
            # handled.
            if len(split_args) == 2:
                self.username = base64.b64decode(arg.split(' ')[1])
                self.push('334 ' + base64.b64encode('Username'))
            else:
                self.push('334 ' + base64.b64encode('Username'))

        elif not self.username:
            self.username = base64.b64decode(arg)
            self.push('334 ' + base64.b64encode('Password'))
        else:
            self.authenticating = False
            self.password = base64.b64decode(arg)
            if self.credential_validator and \
               self.credential_validator.validate(self.username, self.password):
                self.authenticated = True
                self.push('235 Authentication successful.')
            else:
                self.push('454 Temporary authentication failure.')
                #raise asyncore.ExitNow()

    def _smtp_STARTTLS(self, arg):
        if arg:
            self.push('501 Syntax: STARTTLS')
        else:
            self.push('220 Go ahead with TLS')
            conn = self.__conn
            server = self.__server

            conn.setblocking(1)
            conn.settimeout(TIMEOUT)
            conn = ssl.wrap_socket(
                conn,
                server_side=True,
                certfile=server.certfile,
                keyfile=server.keyfile,
                ssl_version=server.ssl_version
            )

            self.__conn = conn
            self.set_socket(conn)
            LOG.info('Entered TLS mode')


class SecureSMTPServer(smtpd.SMTPServer):

    def __init__(self, localaddr, remoteaddr, ssl=False, certfile=None,
                 keyfile=None, ssl_version=ssl.PROTOCOL_SSLv23, tls=False,
                 require_authentication=False, credential_validator=None):
        smtpd.SMTPServer.__init__(self, localaddr, remoteaddr)
        self.certfile = certfile
        self.keyfile = keyfile
        self.ssl_version = ssl_version
        self.subprocesses = []
        self.require_authentication = require_authentication
        self.credential_validator = credential_validator
        self.ssl = ssl
        self.tls = tls
        # self.debug = True

    def listen(self, num):
        return smtpd.SMTPServer.listen(self, num * 10)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            conn, addr = pair
            #channel = smtpd.SMTPChannel(self, conn, addr)
            #AuthSMTPChannel(self, conn, addr)
            if self.ssl:
#                 try:
                    conn.settimeout(TIMEOUT)
                    conn = ssl.wrap_socket(
                        conn,
                        server_side=True,
                        certfile=self.certfile,
                        keyfile=self.keyfile,
                        ssl_version=self.ssl_version,
                    )
#                 except Exception, e:
#                     LOG.error(e)
#                     self.close()
#                     return
            AuthSMTPChannel(self, conn, addr)


class CustomSMTPServer(smtpd.SMTPServer):

    def process_message(self, peer, mailfrom, rcpttos, data):
        print 'Receiving message from:', peer
        print 'Message addressed from:', mailfrom
        print 'Message addressed to  :', rcpttos
        print 'Message length        :', len(data)
        self.close()
        return


def smtp_server(callback, address=None, port=1025, timeout=TIMEOUT,
                credentials=None, ssl=False, ssl_version=ssl.PROTOCOL_SSLv23,
                tls=False, use_auth=False):
    assert callable(callback)
    if not address:
        address = get_local_ip(MGMT_HOST)
    if use_auth:
        assert credentials
    SecureSMTPServer.process_message = callback

    # ssl wants the cert in a file :(
    with tempfile.NamedTemporaryFile('wt', delete=False) as ntf:
        ntf.write(SSL_KEY + "\n" + SSL_CRT + "\n")

    # Waiting for the port to be released (if already in use)
    server = wait(lambda: SecureSMTPServer((address, port), None,
                          ssl=ssl, ssl_version=ssl_version, certfile=ntf.name,
                          require_authentication=use_auth, tls=tls,
                          credential_validator=CredentialValidator(credentials)),
                  progress_cb=lambda x: 'address/port in use',
                  timeout=TIMEOUT, interval=1)
    server.shutdown = False

    t = MailListener(server, timeout, ntf)
    t.start()
    return address, port, t
