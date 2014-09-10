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
from f5test.web.validators import validators, min_version_validator


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
@bottle.jinja2_view('bvt_basic', template_lookup=TEMPLATE_DIR)
def bvt_basic_view(task_id=None):
    return AttrDict(name='Hello world')


@app.get('/bvt/bigiq')
@bottle.jinja2_view('bvt_bigiq', template_lookup=TEMPLATE_DIR)
def bvt_bigiq_view(task_id=None):
    return AttrDict(name='Hello world')

@app.get('/bvt/deviso')
@bottle.jinja2_view('bvt_deviso', template_lookup=TEMPLATE_DIR)
def bvt_deviso_view(task_id=None):
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
        result.logs[:] = result.logs[int(offset):]
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
    data = json.load(bottle.request.body)
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
    our_config.update({'plugins': {'email': {'to': []}}})
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
    params.product = 'bigip'

    if not min_version_validator(params.build, params.version, params.hotfix,
                                 params.product, CONFIG.supported):
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
        args.append('{VENV}/tests/solar/bvt/')

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
    data = json.load(bottle.request.body)

    our_config = AttrDict(yaml.load(open(get_harness('bigiq-tmos')).read()))

    # Prepare placeholders in our config
    our_config.update({'stages': {'main': {'setup': {'install-bigips': {'parameters': {}}}}}})
    our_config.update({'plugins': {'email': {'to': []}}})
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
    params.product = 'bigip'

    if not min_version_validator(params.build, params.version, params.hotfix,
                                 params.product, CONFIG.supported):
        # raise ValueError('Requested version not supported')
        bottle.response.status = 406
        return dict(message='Requested version not supported')

    args = []
    args[:] = NOSETESTS_ARGS

    args.append('--tc-file={VENV}/%s' % CONFIG_FILE)
    args.append('--tc=stages.enabled:1')
    # For bigtime
    # args.append('--attr=status=CONFIRMED,priority=1')
    # args.append('--eval-attr=status is not "DISABLED"')
    # For chuckanut++
    args.append('--eval-attr=rank >= 5 and rank <= 10')
    args.append('--with-email')
    args.append('--with-bvtinfo')
    args.append('--with-irack')
    # args.append('{VENV}/%s' % TEST_ROOT_STABLE)
    args.append('{VENV}/%s' % CONFIG.paths.tc)

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
    # BIGIP_VERSION = '11.5.0'
    # BIGIP_HOTFIX = None
    # BIGIP_BUILD = None

    # For people who don't like to set the application/json header.
    data = json.load(bottle.request.body)
    # data = bottle.request.json

#    with IrackInterface(address=CONFIG.irack.address,
#                        timeout=30,
#                        username=CONFIG.irack.username,
#                        password=CONFIG.irack.apikey,
#                        ssl=False) as irack:
#        config_dir = os.path.dirname(CONFIG_FILE)
#        harness_files = [os.path.join(config_dir, x) for x in CONFIG.web.harnesses]
#        our_config = RCMD.irack.pick_best_harness(harness_files, ifc=irack)
    our_config = AttrDict(yaml.load(open(get_harness('bigiq')).read()))

    # Prepare placeholders in our config
    our_config.update({'stages': {'main': {'setup': {'install': {'parameters': {}}}}}})
    our_config.update({'stages': {'main': {'setup': {'install-bigips': {'parameters': {}}}}}})
    our_config.update({'plugins': {'email': {'to': []}}})

    plugins = our_config.plugins
    # Append submitter's email to recipient list
    if data.get('email'):
        plugins.email.to.append(data['email'])
    plugins.email.to.extend(CONFIG.web.recipients)

    # Set version and build in the install stage
    if data['iso']:
        params = our_config.stages.main.setup['install'].parameters
        params['custom iso'] = data['iso']

    # params = our_config.stages.main.setup['install-bigips'].parameters
    # params.version = BIGIP_VERSION
    # params.hotfix = BIGIP_HOTFIX
    # params.build = BIGIP_BUILD

    args = []
    args[:] = NOSETESTS_ARGS

    args.append('--tc-file={VENV}/%s' % CONFIG_FILE)

    # Default is our BVT suite.
    suite = SUITES[data.get('suite', DEFAULT_SUITE)]
    args.append('--tc=stages.enabled:1')
    # XXX: No quotes around the long argument value!
    if data.get('suite') == DEFAULT_SUITE:
        args.append('--eval-attr=rank > 0 and rank < 11')
    args.append('--with-email')
    # args.append('--with-bvtinfo')
    args.append('--with-irack')
    args.append('{VENV}/%s' % suite)

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


if __name__ == '__main__':
    # app.run(host='0.0.0.0', server='gevent', port=PORT, debug=DEBUG)
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
