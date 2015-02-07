"""Friendly Python SSH2 interface."""

import glob
import logging
import os
import socket
import stat
import time

import paramiko

from ...utils.net import get_local_ip


LOG = logging.getLogger(__name__)
SSH_DIR = os.path.join(os.path.expanduser('~'), '.ssh')
KEEPALIVE = 60


class SSHTimeoutError(Exception):
    pass


class SSHResult(object):

    def __init__(self, status, stdout, stderr, command=None):
        self.status = int(status) or 0
        self.stdout = stdout
        self.stderr = stderr
        self.command = command

    def __str__(self):
        outdict = self.__dict__
        cutoff = 512

        if len(self.stdout) > cutoff:
            outdict['stdout'] = self.stdout[:cutoff] + '...'
        if len(self.stderr) > cutoff:
            outdict['stderr'] = self.stderr[:cutoff] + '...'

        if self.command:
            return "SSHResult: '%(command)s' -> " \
                "status=%(status)d:stdout=%(stdout)s:stderr=%(stderr)s" % outdict
        return "SSHResult: " \
            "status=%(status)d:stdout=%(stdout)s:stderr=%(stderr)s" % outdict


class Connection(paramiko.SSHClient):
    """A friendlier wrapper around paramiko.SSHClient.

    It provides 4 important methods:
        run - execute comands on a remote machine
        put - transfer a file to the remote machine
        get - transfer a file from the remote machine
        exchange_key - do a SSH key exchange

    @param address: the server to connect to
    @type address: str
    @param port: the server port to connect to
    @type port: int
    @param username: the username to authenticate as (defaults to the
        current local username)
    @type username: str
    @param password: a password to use for authentication or for unlocking
        a private key
    @type password: str
    @param timeout: an optional timeout (in seconds) for the TCP connect
    @type timeout: float
    @param look_for_keys: set to False to disable searching for discoverable
        private key files in C{~/.ssh/}
    @type look_for_keys: bool
    """
    def __init__(self,
                 address,
                 username=None,
                 password=None,
                 key_filename=None,
                 port=22,
                 timeout=180,
                 look_for_keys=False
                 ):
        self._sftp_live = False
        self._sftp = None
        self.__dict__.update(locals())
        self.__dict__.pop('self')
        super(Connection, self).__init__()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Closes the underlying transport.
        """
        self.close()

    def __repr__(self):
        return '<SSH Connection: %s:%s@%s:%d>' % (self.username, self.password,
                                                  self.address, self.port)

    def is_connected(self):
        return bool(self._transport and self._transport.active)

    def exists(self, filename):
        try:
            self.stat(filename)
            return True
        except IOError:
            return False

    def connect(self):
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        super(Connection, self).connect(self.address, self.port,
                                        self.username, self.password,
                                        key_filename=self.key_filename,
                                        timeout=self.timeout,
                                        look_for_keys=self.look_for_keys)
        self.get_transport().set_keepalive(KEEPALIVE)

    def run(self, command, bufsize=-1):
        """Execute a command remotely."""
        if not self.is_connected():
            LOG.warning('SSH channel lost. Reconnecting...')
            self.connect()
        chan = self._transport.open_session()

        LOG.debug('run: %s on %s...', command, self)
        chan.settimeout(self.timeout)
        chan.exec_command(command)
        stdout = chan.makefile('rb', bufsize)
        stderr = chan.makefile_stderr('rb', bufsize)

        try:
            ret = SSHResult(-1, stdout.read(), stderr.read(), command)
            ret.status = chan.recv_exit_status()
            if ret.status != 0:
                LOG.debug(ret.stdout)
                LOG.debug(ret.stderr)
                LOG.warning("Non zero status: %s", ret)
            return ret
        except socket.timeout:
            self.close()
            raise SSHTimeoutError("running `%s`" % command)

    def run_wait(self, command, progress=None, bufsize=-1, interval=1):
        """Execute a command remotely and execute progress every N secs."""
        assert self.is_connected(), "SSH channel not connected"
        chan = self._transport.open_session()

        status = None

        chan.settimeout(self.timeout)
        LOG.debug('run_wait: %s on %s', command, self)
        chan.exec_command(command)
        max_loops = 1.0 / interval * self.timeout
        LOG.debug('exec timeout: %d', self.timeout)

        stdout = []
        stderr = []

        def read_channel(chan):
            chunkout = chunkerr = ''
            if chan.recv_ready():
                chunkout = chan.recv(bufsize)
                if chunkout:
                    stdout.append(chunkout)

            if chan.recv_stderr_ready():
                chunkerr = chan.recv_stderr(bufsize)
                if chunkerr:
                    stderr.append(chunkerr)

            if chunkout or chunkerr:
                progress(chunkout.strip(), chunkerr.strip())

        i = 0
        try:
            while not chan.exit_status_ready():
                read_channel(chan)
                time.sleep(interval)
                i += 1
                if i > max_loops:
                    raise SSHTimeoutError("running `%s`" % command)

            read_channel(chan)
            status = chan.recv_exit_status()
            return SSHResult(status, ''.join(stdout), ''.join(stderr), command)
        except socket.timeout:
            self.close()
            raise SSHTimeoutError("running `%s`" % command)

    def _sftp_connect(self):
        """Establish the SFTP connection.
        """
        if not self.is_connected():
            LOG.warning('SSH channel lost. Reconnecting...')
            self.connect()
        if not self._sftp_live:
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
            self._sftp_live = True

    def sftp(self):
        self._sftp_connect()
        return self._sftp

    def get(self, remotepath, localpath=None, move=False):
        """Download a remote file or multiple matching a glob pattern.
        get('/var/log/file.out', '/tmp')
        """
        if not localpath:
            localpath = os.path.basename(remotepath)
        self._sftp_connect()
        LOG.debug('get: %s -> %s on %s...', remotepath, localpath, self)

        if glob.has_magic(remotepath):
            assert os.path.isdir(localpath)
            wildname = os.path.basename(remotepath)
            dirname = os.path.dirname(remotepath)
            for filename in self._sftp.listdir(dirname):
                if glob.fnmatch.fnmatch(filename, wildname):
                    source = os.path.join(dirname, filename)
                    destination = os.path.join(localpath, filename)
                    self._sftp.get(source, destination)
                    if move:
                        self._sftp.remove(source)
        else:
            self._sftp.get(remotepath, localpath)
            if move:
                self._sftp.remove(remotepath)

    def put(self, localpath, remotepath=None):
        """Upload a local file.
        """
        if not remotepath:
            remotepath = os.path.split(localpath)[1]
        LOG.debug('put: %s -> %s on %s...', localpath, remotepath, self)

        self._sftp_connect()
        self._sftp.put(localpath, remotepath)

    def stat(self, path):
        """Retrieve information about a file on the remote system.  The return
        value is an object whose attributes correspond to the attributes of
        python's C{stat} structure as returned by C{os.stat}, except that it
        contains fewer fields.
        """
        self._sftp_connect()
        return self._sftp.stat(path)

    def remove(self, path):
        """Remove the file at the given path.  This only works on files; for
        removing folders (directories), use L{rmdir}.
        """
        self._sftp_connect()
        attrs = self.stat(path)
        if attrs is not None:
            kind = stat.S_IFMT(attrs.st_mode)
            if kind == stat.S_IFDIR:
                return self._sftp.rmdir(path)
            else:
                return self._sftp.remove(path)

    def _load_key(self):
        """Loads an RSA/DSS key from the users home directory and returns it.
        """
        for keyname, keytype in (('id_dsa', paramiko.DSSKey),
                                 ('id_rsa', paramiko.RSAKey)):
            filepath = os.path.join(SSH_DIR, keyname)
            if os.path.isfile(filepath):
                LOG.debug('Loading SSH key %s' % filepath)
                return keytype.from_private_key_file(filepath)
        LOG.debug('No SSH keys to load')
        return None

    def _create_key(self):
        """Generates a DSS key and stores the related files in the user's ~/.ssh
        direcotry.
        """
        LOG.debug('Generating a DSS SSH key')
        key = paramiko.DSSKey.generate()
        if not os.path.exists(SSH_DIR):
            os.mkdir(SSH_DIR)
        private_key_name = os.path.join(SSH_DIR, 'id_dsa')
        key.write_private_key_file(private_key_name)
        f = open('%s.pub' % private_key_name, 'w')
        f.write('%s %s' % (key.get_name(), key.get_base64()))
        f.close()
        return key

    def _load_or_create_key(self):
        """Attempts to load an SSH key using L{load_key()}. If that fails, one is
        generated via L{create_key()}.
        """
        key = self._load_key()
        if key is None:
            key = self._create_key()
        return key

    def _remove_host_key(self):
        """Removes the host from the users known_hosts file.
        """
        filename = os.path.join(SSH_DIR, 'known_hosts')
        if not os.path.isfile(filename):
            LOG.debug('No known_hosts file exists, skipping key removal')
            return False
        f = open(filename)
        contents = f.read()
        f.close()

        # Look for line starting with hostname
        hostline = ''
        new_lines = []
        for line in contents.splitlines(True):
            if line.startswith(self.address):
                hostline = line
            else:
                new_lines.append(line)

        # If it was found, write new contents
        if hostline:
            LOG.debug('Host key found for %s, removing from known_hosts' %
                      self.address)
            f = open(filename, 'w')
            f.write(''.join(new_lines))
            f.close()
            return True
        LOG.debug('Host key for %s not found in known_hosts' % self.address)
        return False

    def exchange_key(self, filename='.ssh/authorized_keys', key=None, name=None):
        """Places an ssh key in a remote authorized_keys file."""
        assert self.is_connected(), "SSH channel not connected"
        if key is None:
            key = self._load_or_create_key()
            self._remove_host_key()

        if name is None:
            name = get_local_ip(self.address)

        sftp = self._transport.open_sftp_client()
        if '.ssh' not in sftp.listdir():
            sftp.mkdir('.ssh')

        hkey = key.get_base64()
        found = False
        try:
            f = sftp.open(filename, 'r')
            for line in f.readlines():
                bits = line.strip().split(' ', 2)
                if len(bits) > 1 and bits[1] == hkey:
                    found = True
                    break
            f.close()
            mode = 'a'
        except IOError:
            mode = 'w'

        if not found:
            f = sftp.open(filename, mode)
            f.write('\n%s %s %s' % (key.get_name(), hkey, name))
            f.close()

    def interactive(self):
        from .paramikospawn import ParamikoSpawn

        assert self.is_connected(), "SSH channel not connected"
        client = ParamikoSpawn(None)
        client.channel = self.invoke_shell()
        # TODO: timeout this loop
        while not client.channel.recv_ready():
            time.sleep(.1)
        return client


def main():
    """Little test when called directly."""

    with Connection('172.27.58.179', username='root', password='default') as myssh:
        myssh.put('ssh.py')
        r = myssh.run('echo "haha!" > haha.txt && sleep 0 && b list')
        print r.status
        myssh.get('haha.txt')
        myssh.exchange_key()

# start the ball rolling.
if __name__ == "__main__":
    main()
