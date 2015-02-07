from . import ssh, tmsh, bigpipe, sql, bigiq

WIPE_STORAGE = 'bigstart stop restnoded restjavad && rm -rf /var/config/rest'\
               ' && bigstart start restjavad && sleep 5 && bigstart start'\
               ' restnoded'
