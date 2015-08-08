from __future__ import absolute_import

import json
import os
import re

import yaml

import bottle
from celery.backends.cache import get_best_memcache
from f5test.base import AttrDict
from f5test.defaults import ADMIN_USERNAME
from f5test.web.tasks import nosetests, add, confgen, install, ictester, MyAsyncResult
from f5test.web.validators import validators, min_version_validator, sanitize_atom_path
from f5test.utils.cm import isofile, version_from_metadata
from f5test.utils.exbuilder.python import Literal, String, In, Or


# from gevent import monkey; monkey.patch_all()
app = bottle.Bottle()
CONFIG = AttrDict()
CONFIG_WEB_FILE = 'config/shared/web.yaml'
VENV = os.environ.get('VIRTUAL_ENV', '../../../')  # When run from Eclipse.
TEMPLATE_DIR = [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'views')]
DEBUG = True
PORT = 8081

# Setup config
CONFIG_WEB_FILE = os.path.join(VENV, CONFIG_WEB_FILE)


def read_config():
    CONFIG.update(yaml.load(open(CONFIG_WEB_FILE).read()))
read_config()


class ReloadConfigPlugin(object):
    ''' This plugin reloads the web.yaml config before every POST. '''
    name = 'reload'
    api = 2

    def apply(self, callback, route):
        def wrapper(*a, **ka):
            if bottle.request.method == 'POST':
                read_config()
            rv = callback(*a, **ka)
            return rv

        return wrapper
app.install(ReloadConfigPlugin())

# Replacing iRack reservation lookup with a round-robin.
config_dir = os.path.dirname(CONFIG_WEB_FILE)
CONFIG.web._MC_KEY = 'MC-5d5f8cb6-2e8d-4462-a1e8-12f5d6c35334'


# Set nosetests arguments
NOSETESTS_ARGS = ['',
                  '--verbose',
                  '--verbosity=2',  # Print test names and result at the console
                  '--all-modules',  # Collect tests from all Python modules
                  '--exe',  # Look in files that have the executable bit set
                  '--nocapture',  # Don't capture stdout
                  '--console-redirect',  # Redirect console to a log file
                  ]


def get_harness(pool):
    mc = get_best_memcache()[0](CONFIG.memcache)
    key = CONFIG.web._MC_KEY + pool
    try:
        i = mc.incr(key)
    except:
        i = mc.set(key, 0)
    harnesses = CONFIG.web.harnesses[pool]
    return os.path.join(config_dir, harnesses[i % len(harnesses)])


@app.get('/add')
@bottle.jinja2_view('add', template_lookup=TEMPLATE_DIR)
def add_view(task_id=None):
    return AttrDict(name='Hello world')


@app.get('/bvt/basic')
@app.get('/bigip_bvt_request')
@bottle.jinja2_view('bvt_basic', template_lookup=TEMPLATE_DIR)
def bvt_basic_view(task_id=None):
    return AttrDict(name='Hello world')


@app.get('/bvt/bigiq')
@app.get('/bigip_bigiq_request')
@bottle.jinja2_view('bvt_bigiq', template_lookup=TEMPLATE_DIR)
def bvt_bigiq_view(task_id=None):
    return AttrDict(name='Hello world')


@app.get('/bvt/deviso')
@bottle.jinja2_view('bvt_deviso', template_lookup=TEMPLATE_DIR)
def bvt_deviso_view(task_id=None):
    return AttrDict(name='Hello world')


@app.get('/bvt/emdeviso')
@bottle.jinja2_view('bvt_emdeviso', template_lookup=TEMPLATE_DIR)
def bvt_emdeviso_view(task_id=None):
    return AttrDict(name='Hello world')


@app.get('/tester/icontrol')
@bottle.jinja2_view('tester_icontrol', template_lookup=TEMPLATE_DIR)
def tester_icontrol_view(task_id=None):
    return AttrDict(name='Hello world')


@app.get('/config')
@bottle.jinja2_view('config', template_lookup=TEMPLATE_DIR)
def config_view(task_id=None):
    return AttrDict(name='Hello world')


@app.get('/')
@app.get('/install')
@bottle.jinja2_view('install', template_lookup=TEMPLATE_DIR)
def install_view(task_id=None):
    return AttrDict(name='Hello world')


@app.get('/deobfuscator')
@bottle.jinja2_view('deobfuscator', template_lookup=TEMPLATE_DIR)
def simple_decrypter_view():
    return AttrDict(name='Hello world')


@app.post('/deobfuscator')
def simple_decrypter_post():
    from Crypto.Cipher import DES
    from base64 import b64decode
    unpad = lambda s: s[0:-ord(s[-1])]  # @IgnorePep8
    data = AttrDict(bottle.request.json)
    try:
        i = data.input.decode('unicode_escape')
        ret = unpad(DES.new('GhVJDUfx').decrypt(b64decode(i)))
    except Exception, e:
        return dict(input=str(e))
    return dict(input=ret)


@app.post('/add')
def add_post():
    data = AttrDict(bottle.request.json)
    result = add.delay(data.number_1 or 0, data.number_2 or 0, user_input=data)  # @UndefinedVariable
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


# Serves static files
@app.route('/media/:path#.+#')
def media(path):
    root = os.path.join(os.path.dirname(__file__), 'media')
    return bottle.static_file(path, root=root)


@app.route('/revoke/<task_id>', name='revoke')
def revoke_handler(task_id):
    task = MyAsyncResult(task_id)  # @UndefinedVariable
    task.revoke(terminate=True)
    task.revoke(terminate=True)  # XXX: why?!
    bottle.response.add_header('Cache-Control', 'no-cache')
    return dict(status=task.status)


@app.route('/status/<task_id>', name='status')
def status_handler(task_id):
    # status = nosetests.delay() #@UndefinedVariable
    task = MyAsyncResult(task_id)  # @UndefinedVariable
    result = task.load_meta()
    offset = bottle.request.query.get('s')
    if offset and result and result.logs:
        last = int(offset) - (result.tip or 0)  # it should be negative
        result.logs[:] = result.logs[last:] if last else []
    value = task.result if task.successful() else None
    bottle.response.add_header('Cache-Control', 'no-cache')
    return dict(status=task.status, value=value, result=result,
                traceback=task.traceback)


@app.post('/validate')
def validate():
    data = AttrDict(bottle.request.json)
    bottle.response.add_header('Cache-Control', 'no-cache')

#    print data
    is_valid = validators[data.type](**data)
    if is_valid is not True:
        bottle.response.status = 406
        return dict(message=is_valid)


# Backward compatible with bvtinfo-style POST requests.
@app.route('/bvt/basic', method='POST')
@app.route('/bigip_bvt_request', method='POST')
def bvt_basic_post():
    """Handles requests from BIGIP teams.

    All the logic needed to translate the user input into what makes sense to
    us happens right here.
    """
    BVTINFO_PROJECT_PATTERN = '(\D+)?(\d+\.\d+\.\d+)-?(eng-?\w*|hf\d+|hf-\w+)?'
    TESTS_DEBUG = 'tests/solar/bvt/integration/filesystem/'
    CONFIG_FILE = 'config/shared/web_bvt_request.yaml'

    # For people who don't like to set the application/json header.
    data = AttrDict(json.load(bottle.request.body))
    data._referer = bottle.request.url
    # data = bottle.request.json

    # BUG: The iRack reservation-based picker is flawed. It'll always select
    # the nearest available harness, stacking all workers on just one.
#    with IrackInterface(address=CONFIG.irack.address,
#                        timeout=30,
#                        username=CONFIG.irack.username,
#                        password=CONFIG.irack.apikey,
#                        ssl=False) as irack:
#        config_dir = os.path.dirname(CONFIG_WEB_FILE)
#        harness_files = [os.path.join(config_dir, x) for x in CONFIG.web.harnesses]
#        our_config = RCMD.irack.pick_best_harness(harness_files, ifc=irack)
    our_config = AttrDict(yaml.load(open(get_harness('em')).read()))

    # Prepare placeholders in our config
    our_config.update({'stages': {'main': {'setup': {'install-bigips': {'parameters': {}}}}}})
    our_config.update({'plugins': {'email': {'to': [], 'variables': {}}}})
    our_config.update({'plugins': {'bvtinfo': {}}})

    plugins = our_config.plugins
    # Set BVTInfo data
    plugins.bvtinfo.project = data['project']
    plugins.bvtinfo.build = data['build']

    # Append submitter's email to recipient list
    if data.get('submitted_by'):
        plugins.email.to.append(data['submitted_by'])
    plugins.email.to.extend(CONFIG.web.recipients)

    # Set version and build in the install stage
    params = our_config.stages.main.setup['install-bigips'].parameters
    match = re.match(BVTINFO_PROJECT_PATTERN, data['project'])
    if match:
        params['version'] = match.group(2)
        if match.group(3):
            params['hotfix'] = match.group(3)
    else:
        params['version'] = data['project']
    params['build'] = data['build']
    params['custom iso'] = data.get('custom_iso')
    params['custom hf iso'] = data.get('custom_hf_iso')
    params.product = 'bigip'

    if not min_version_validator(params.build, params.version, params.hotfix,
                                 params.product, min_ver=CONFIG.supported):
        # raise ValueError('Requested version not supported')
        bottle.response.status = 406
        return dict(message='Requested version not supported')

    args = []
    args[:] = NOSETESTS_ARGS

    args.append('--tc-file={VENV}/%s' % CONFIG_FILE)
    if data.get('debug'):
        args.append('--tc=stages.enabled:1')
        tests = [os.path.join('{VENV}', x)
                 for x in re.split('\s+', (data.get('tests') or TESTS_DEBUG).strip())]
        args.extend(tests)
    else:
        args.append('--tc=stages.enabled:1')
        args.append('--eval-attr=rank > 0 and rank < 11')
        args.append('--with-email')
        args.append('--with-bvtinfo')
        args.append('--with-irack')
        args.append('{VENV}/%s' % CONFIG.paths.em)

    v = plugins.email.variables
    v.args = args
    v.project = data['project']
    v.version = params.version
    v.build = params.build

    result = nosetests.delay(our_config, args, data)  # @UndefinedVariable
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


# Backward compatible with bvtinfo-style POST requests.
@app.route('/bvt/bigiq', method='POST')
@app.route('/bigip_bigiq_request', method='POST')
def bvt_bigiq_post():
    """Handles requests from BIGIP teams for BIGIQ BVT.

    All the logic needed to translate the user input into what makes sense to
    us happens right here.
    """
    BVTINFO_PROJECT_PATTERN = '(\D+)?(\d+\.\d+\.\d+)-?(eng-?\w*|hf\d+|hf-\w+)?'
    CONFIG_FILE = 'config/shared/web_bvt_request_bigiq.yaml'

    # For people who don't like to set the application/json header.
    data = AttrDict(json.load(bottle.request.body))
    data._referer = bottle.request.url

    our_config = AttrDict(yaml.load(open(get_harness('bigiq-tmos')).read()))

    # Prepare placeholders in our config
    our_config.update({'stages': {'main': {'setup': {'install-bigips': {'parameters': {}}}}}})
    our_config.update({'plugins': {'email': {'to': [], 'variables': {}}}})
    our_config.update({'plugins': {'bvtinfo': {'bigip': {}}}})

    plugins = our_config.plugins
    # Set BVTInfo data
    plugins.bvtinfo.project = data['project']
    plugins.bvtinfo.build = data['build']
    plugins.bvtinfo.bigip.name = 'bigiq-bvt'

    # Append submitter's email to recipient list
    if data.get('submitted_by'):
        plugins.email.to.append(data['submitted_by'])
    plugins.email.to.extend(CONFIG.web.recipients)

    # Set version and build in the install stage
    params = our_config.stages.main.setup['install-bigips'].parameters
    match = re.match(BVTINFO_PROJECT_PATTERN, data['project'])
    if match:
        params['version'] = match.group(2)
        if match.group(3):
            params['hotfix'] = match.group(3)
    else:
        params['version'] = data['project']
    params['build'] = data['build']
    params['custom iso'] = data.get('custom_iso')
    params['custom hf iso'] = data.get('custom_hf_iso')
    params.product = 'bigip'

    if not min_version_validator(params.build, params.version, params.hotfix,
                                 params.product, min_ver=CONFIG.supported):
        # raise ValueError('Requested version not supported')
        bottle.response.status = 406
        return dict(message='Requested version not supported')

    args = []
    args[:] = NOSETESTS_ARGS

    args.append('--tc-file={VENV}/%s' % CONFIG_FILE)
    args.append('--tc=stages.enabled:1')
    # For chuckanut++
    args.append('--eval-attr=rank >= 5 and rank <= 10')
    args.append('--with-email')
    args.append('--with-bvtinfo')
    args.append('--with-irack')
    args.append('{VENV}/%s' % CONFIG.paths.tc)

    v = plugins.email.variables
    v.args = args
    v.project = data['project']
    v.version = params.version
    v.build = params.build

    # return dict(config=our_config, args=args)
    result = nosetests.delay(our_config, args, data)  # @UndefinedVariable
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


@app.route('/bvt/deviso', method='POST')
def bvt_deviso_post():
    """Handles requests from Dev team for user builds ISOs.
    """
    # BVTINFO_PROJECT_PATTERN = '(\D+)?(\d+\.\d+\.\d+)-?(hf\d+)?'
    DEFAULT_SUITE = 'bvt'
    SUITES = {'bvt': '%s/' % CONFIG.paths.current,
              'dev': '%s/cloud/external/devtest_wrapper.py' % CONFIG.paths.current,
              'dev-cloud': '%s/cloud/external/restservicebus.py' % CONFIG.paths.current
              }
    CONFIG_FILE = 'config/shared/web_deviso_request.yaml'

    # For people who don't like to set the application/json header.
    data = AttrDict(json.load(bottle.request.body))
    # data = bottle.request.json
    data._referer = bottle.request.url

    our_config = AttrDict(yaml.load(open(get_harness('bigiq')).read()))

    # Prepare placeholders in our config
    our_config.update({'stages': {'main': {'setup': {'install': {'parameters': {}}}}}})
    our_config.update({'stages': {'main': {'setup': {'install-bigips': {'parameters': {}}}}}})
    our_config.update({'plugins': {'email': {'to': [], 'variables': {}}}})

    plugins = our_config.plugins
    # Append submitter's email to recipient list
    if data.get('email'):
        plugins.email.to.append(data['email'])
    plugins.email.to.extend(CONFIG.web.recipients)

    # Set version and build in the install stage
    v = None
    if data.get('iso'):
        params = our_config.stages.main.setup['install'].parameters
        params['custom iso'] = data['iso']
        v = version_from_metadata(data['iso'])

    if data.get('hfiso'):
        params = our_config.stages.main.setup['install'].parameters
        params['custom hf iso'] = data['hfiso']
        v = version_from_metadata(data['hfiso'])
        # Find the RTM ISO that goes with this HF image.
        if not data.get('iso'):
            params['custom iso'] = isofile(v.version, product=str(v.product))

    args = []
    args[:] = NOSETESTS_ARGS

    rank = Literal('rank')
    expr = (rank > Literal(0)) & (rank < Literal(11))
    # Include all migrated tests, example: functional/standalone/security/migrated/...
    # Assumption is that all tests are rank=505
    expr |= rank == Literal(505)
    # Only Greenflash tests have extended attributes
    if v is None or v >= 'bigiq 4.5':
        # build hamode argument
        if data.ha:
            hamode = Literal('hamode')
            expr2 = Or()
            for x in data.ha:
                if x != 'standalone':
                    expr2 += [In(String(x.upper()), hamode)]
            if 'standalone' in data.ha:
                expr &= (~hamode | expr2)
            else:
                expr &= hamode & expr2

        if data.ui:
            uimode = Literal('uimode')
            if data.ui == 'api':
                expr &= ~uimode
            elif data.ui == 'ui':
                expr &= uimode & (uimode > Literal(0))
            else:
                raise ValueError('Unknown value {}'.format(data.ui))

        if data.module:
            module = Literal('module')
            expr2 = Or()
            for x in data.module:
                expr2 += [In(String(x.upper()), module)]
            expr &= (module & expr2)

    args.append('--tc-file={VENV}/%s' % CONFIG_FILE)

    # Default is our BVT suite.
    if v:
        suite = os.path.join(CONFIG.suites.root, CONFIG.suites[v.version])
    else:
        suite = SUITES[data.get('suite', DEFAULT_SUITE)]
    args.append('--tc=stages.enabled:1')
    # XXX: No quotes around the long argument value!
    args.append('--eval-attr={}'.format(str(expr)))
    args.append('--with-email')
    # args.append('--collect-only')
    args.append('--with-irack')
    args.append('{VENV}/%s' % suite)

    v = plugins.email.variables
    v.args = args
    v.iso = data.iso
    v.module = data.module

    result = nosetests.delay(our_config, args, data)  # @UndefinedVariable
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


@app.route('/bvt/emdeviso', method='POST')
def bvt_emdeviso_post():
    """Handles requests from BIGIP teams.

    All the logic needed to translate the user input into what makes sense to
    us happens right here.
    """
    CONFIG_FILE = 'config/shared/web_emdeviso_request.yaml'

    # For people who don't like to set the application/json header.
    data = AttrDict(json.load(bottle.request.body))
    data._referer = bottle.request.url

    our_config = AttrDict(yaml.load(open(get_harness('em')).read()))

    # Prepare placeholders in our config
    our_config.update({'stages': {'main': {'setup': {'install': {'parameters': {}}}}}})
    our_config.update({'plugins': {'email': {'to': [], 'variables': {}}}})

    plugins = our_config.plugins

    # Append submitter's email to recipient list
    if data.get('email'):
        plugins.email.to.append(data['email'])
    plugins.email.to.extend(CONFIG.web.recipients)

    # Set version and build in the install stage
    v = None
    if data.get('iso'):
        params = our_config.stages.main.setup['install'].parameters
        params['custom iso'] = data['iso']
        v = version_from_metadata(data['iso'])

    if data.get('hfiso'):
        params = our_config.stages.main.setup['install'].parameters
        params['custom hf iso'] = data['hfiso']
        v = version_from_metadata(data['hfiso'])
        # Find the RTM ISO that goes with this HF image.
        if not data.get('iso'):
            params['custom iso'] = isofile(v.version, product=str(v.product))

    args = []
    args[:] = NOSETESTS_ARGS

    args.append('--tc-file={VENV}/%s' % CONFIG_FILE)
    args.append('--tc=stages.enabled:1')
    args.append('--eval-attr=rank > 0 and rank < 11')
    args.append('--with-email')
    #args.append('--with-bvtinfo')
    args.append('--with-irack')
    args.append('{VENV}/%s' % CONFIG.paths.em)

    result = nosetests.delay(our_config, args, data)  # @UndefinedVariable
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


@app.route('/config', method='POST')
def config_post():
    """Handles confgen requests.
    """
    data = AttrDict(bottle.request.json)
    options = AttrDict(data)
    options.provision = ','.join(data.provision)
    options.irack_address = CONFIG.irack.address
    options.irack_username = CONFIG.irack.username
    options.irack_apikey = CONFIG.irack.apikey
    # options.clean = True
    options.no_sshkey = True
    if options.clean:
        options.selfip_internal = None
        options.selfip_external = None
        options.provision = None
        options.timezone = None

    result = confgen.delay(address=data.address.strip(), options=options,  # @UndefinedVariable
                           user_input=data)
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


@app.route('/install', method='POST')
def install_post():
    """Handles install requests.
    """
    data = AttrDict(bottle.request.json)
    options = AttrDict()
    options.admin_password = data.admin_password
    options.root_password = data.root_password
    options.product = data.product
    options.pversion = data.version
    options.pbuild = data.build or None
    options.phf = data.hotfix
    options.image = data.customiso
    if data.format == 'volumes':
        options.format_volumes = True
    elif data.format == 'partitions':
        options.format_partitions = True
    options.timeout = 900
    if data.config == 'essential':
        options.essential_config = True

    result = install.delay(address=data.address.strip(), options=options,  # @UndefinedVariable
                           user_input=data)
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


@app.route('/tester/icontrol', method='POST')
def tester_icontrol_post():
    """Handles icontrol tester requests.
    """
    data = AttrDict(bottle.request.json)
    options = AttrDict()
    options.username = ADMIN_USERNAME
    options.password = data.password
    options.json = True

    result = ictester.delay(address=data.address.strip(), method=data.method,  # @UndefinedVariable
                            options=options,
                            params=data.arguments, user_input=data)

    # print arguments
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


@app.route('/atom_em_bvt', method='POST')
def bvt_basic_post2():
    """Handles EM BVT requests.
    """
    HOOK_NAME = 'em-bvt'
    TESTS_DEBUG = 'tests/solar/bvt/integration/filesystem/'
    CONFIG_FILE = 'config/shared/web_bvt_request.yaml'

    data = AttrDict(json.load(bottle.request.body))
    data._referer = bottle.request.url

    our_config = AttrDict(yaml.load(open(get_harness('em')).read()))

    # Prepare placeholders in our config
    our_config.update({'stages': {'main': {'setup': {'install-bigips': {'parameters': {}}}}}})
    our_config.update({'plugins': {'email': {'to': [], 'variables': {}}}})
    our_config.update({'plugins': {'atom': {'bigip': {}}, 'bvtinfo': {}}})

    plugins = our_config.plugins
    # Set ATOM data
    plugins.atom.bigip.request_id = data.content.id
    plugins.atom.bigip.name = HOOK_NAME

    # Append submitter's email to recipient list
    if data.content.requestor.email:
        plugins.email.to.append(data.content.requestor.email)
    plugins.email.to.extend(CONFIG.web.recipients)

    # Set version and build in the install stage
    params = our_config.stages.main.setup['install-bigips'].parameters

    branch = data.content.build.branch
    version = data.content.build.version
    params['version'] = branch.name
    params['build'] = version.primary
    if int(version.level):
        params['hotfix'] = version.level
        params['custom hf iso'] = sanitize_atom_path(data.content.build.iso)
    else:
        params['custom iso'] = sanitize_atom_path(data.content.build.iso)
    params.product = 'bigip'

    # TODO: Remove this when bvtinfo goes offline
    # Set BVTInfo data
    plugins.bvtinfo.project = branch.name
    plugins.bvtinfo.build = version.old_build_number

    args = []
    args[:] = NOSETESTS_ARGS

    args.append('--tc-file={VENV}/%s' % CONFIG_FILE)
    if data.get('debug'):
        args.append('--tc=stages.enabled:1')
        tests = [os.path.join('{VENV}', x)
                 for x in re.split('\s+', (data.get('tests') or TESTS_DEBUG).strip())]
        args.extend(tests)
    else:
        args.append('--tc=stages.enabled:1')
        args.append('--eval-attr=rank > 0 and rank < 11')
        args.append('--with-email')
        args.append('--with-atom')
        args.append('--with-bvtinfo')
        if not min_version_validator(params.build, params.version, params.hotfix,
                                     params.product, iso=data.content.build.iso,
                                     min_ver=CONFIG.supported):
            args.append('--with-atom-no-go=The requested product/version is not supported by this test suite.')

        args.append('--with-irack')
        # args.append('--with-qkview=never')
        # args.append('{VENV}/tests/solar/bvt/')
        args.append('{VENV}/%s' % CONFIG.paths.em)

    v = plugins.email.variables
    v.args = args
    v.project = data.content.build.branch.name
    v.version = data.content.build.version.version
    v.build = data.content.build.version.build

    result = nosetests.delay(our_config, args, data)  # @UndefinedVariable
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


@app.route('/bvt/atom_bigiq_bvt', method='POST')
def bvt_bigiq_post2():
    """Handles requests from BIGIP teams for BIGIQ BVT.

    All the logic needed to translate the user input into what makes sense to
    us happens right here.
    """
    HOOK_NAME = 'big-iq-bvt'
    CONFIG_FILE = 'config/shared/web_bvt_request_bigiq.yaml'

    data = AttrDict(json.load(bottle.request.body))
    data._referer = bottle.request.url

    our_config = AttrDict(yaml.load(open(get_harness('bigiq-tmos')).read()))

    # Prepare placeholders in our config
    our_config.update({'stages': {'main': {'setup': {'install-bigips': {'parameters': {}}}}}})
    our_config.update({'plugins': {'email': {'to': [], 'variables': {}}}})
    our_config.update({'plugins': {'atom': {'bigip': {}}, 'bvtinfo': {}}})

    plugins = our_config.plugins
    # Set ATOM data
    plugins.atom.bigip.request_id = data.content.id
    plugins.atom.bigip.name = HOOK_NAME

    # Append submitter's email to recipient list
    if data.content.requestor.email:
        plugins.email.to.append(data.content.requestor.email)
    plugins.email.to.extend(CONFIG.web.recipients)

    # Set version and build in the install stage
    params = our_config.stages.main.setup['install-bigips'].parameters

    branch = data.content.build.branch
    version = data.content.build.version
    params['version'] = branch.name
    params['build'] = version.primary
    if int(version.level):
        params['hotfix'] = version.level
        params['custom hf iso'] = sanitize_atom_path(data.content.build.iso)
    else:
        params['custom iso'] = sanitize_atom_path(data.content.build.iso)
    params.product = 'bigip'

    # TODO: Remove this when bvtinfo goes offline
    # Set BVTInfo data
    plugins.bvtinfo.project = branch.name
    plugins.bvtinfo.build = version.old_build_number

    args = []
    args[:] = NOSETESTS_ARGS

    args.append('--tc-file={VENV}/%s' % CONFIG_FILE)
    args.append('--tc=stages.enabled:1')
    # For chuckanut++
    args.append('--eval-attr=rank >= 5 and rank <= 10')
    args.append('--with-email')
    args.append('--with-atom')
    args.append('--with-bvtinfo')
    if not min_version_validator(params.build, params.version, params.hotfix,
                                 params.product, iso=data.content.build.iso,
                                 min_ver=CONFIG.supported):
        args.append('--with-atom-no-go=The requested product/version is not supported by this test suite.')
    args.append('--with-irack')
    # args.append('--with-qkview=never')
    args.append('{VENV}/%s' % CONFIG.paths.tc)
    # args.append('{VENV}/tests/firestone/functional/standalone/adc/api/')

    v = plugins.email.variables
    v.args = args
    v.project = data.content.build.branch.name
    v.version = data.content.build.version.version
    v.build = data.content.build.version.build

    # return dict(config=our_config, args=args)
    result = nosetests.delay(our_config, args, data)  # @UndefinedVariable
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


if __name__ == '__main__':
    # app.run(host='0.0.0.0', server='gevent', port=PORT, debug=DEBUG)
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
