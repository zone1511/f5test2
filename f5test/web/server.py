from __future__ import absolute_import

from f5test.base import AttrDict
from f5test.defaults import ADMIN_USERNAME
from f5test.web.tasks import nosetests, add, confgen, install, ictester, MyAsyncResult
from f5test.web.validators import validators
from celery.backends.cache import get_best_memcache
#from gevent import monkey; monkey.patch_all()
import bottle
import os
import json
import yaml
import re

app = bottle.Bottle()
CONFIG = AttrDict()
CONFIG_WEB_FILE = 'config/web.yaml'
VENV = os.environ.get('VIRTUAL_ENV', '../../../')  # When run from Eclipse.
TEMPLATE_DIR = [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'views')]
DEBUG = True
PORT = 8081


# Setup config
CONFIG_WEB_FILE = os.path.join(VENV, CONFIG_WEB_FILE)
CONFIG.update(yaml.load(open(CONFIG_WEB_FILE).read()))

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
    '--nologcapture',  # We have our own logcollect which is better
    '--console-redirect',  # Redirect console to a log file
]


def get_harness():
    mc = get_best_memcache(CONFIG.memcache)
    try:
        i = mc.incr(CONFIG.web._MC_KEY)
    except:
        i = mc.set(CONFIG.web._MC_KEY, 0)
    return os.path.join(config_dir,
                        CONFIG.web.harnesses[i % len(CONFIG.web.harnesses)])


@app.get('/add')
@bottle.jinja2_view('add', template_lookup=TEMPLATE_DIR)
def add_view(task_id=None):
    return AttrDict(name='Hello world')


@app.get('/bvt/basic')
@bottle.jinja2_view('bvt_basic', template_lookup=TEMPLATE_DIR)
def bvt_basic_view(task_id=None):
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
    #status = nosetests.delay() #@UndefinedVariable
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
    BVTINFO_PROJECT_PATTERN = '(\D+)?(\d+\.\d+\.\d+)-?(hf\d+)?'
    TESTS_DEBUG = 'tests/solar/bvt/integration/filesystem/'
    CONFIG_FILE = 'config/suite_bvt_request.yaml'

    # For people who don't like to set the application/json header.
    data = json.load(bottle.request.body)
    #data = bottle.request.json

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
    our_config = AttrDict(yaml.load(open(get_harness()).read()))

    # Prepare placeholders in our config
    our_config.update({'stages': {'main': {'setup': {'stage01-install-bigip-1': {'parameters': {}}}}}})
    our_config.update({'bvtinfo': {}})
    our_config.update({'email': {'to': []}})

    # Set BVTInfo data
    our_config.bvtinfo.project = data['project']
    our_config.bvtinfo.build = data['build']

    # Append submitter's email to recipient list
    if data.get('submitted_by'):
        our_config.email.to.append(data['submitted_by'])
    our_config.email.to.extend(CONFIG.web.recipients)

    # Set version and build in the install stage
    params = our_config.stages.main.setup['stage01-install-bigip-1'].parameters
    match = re.match(BVTINFO_PROJECT_PATTERN, data['project'])
    if match:
        params['version'] = match.group(2)
        if match.group(3):
            params['hotfix'] = match.group(3)
    else:
        params['version'] = data['project']
    params['build'] = data['build']

    args = []
    args[:] = NOSETESTS_ARGS

    args.append('--tc-file={VENV}/%s' % CONFIG_FILE)
    if data.get('debug'):
        args.append('--tc=stages._enabled:1')
        args.append('--no-email')
        tests = [os.path.join('{VENV}', x)
                for x in re.split('\s+', (data.get('tests') or TESTS_DEBUG).strip())]
        #print tests
        #return
        args.extend(tests)
    else:
        args.append('--tc=stages._enabled:1')
        args.append('--attr=status=CONFIRMED,priority=1')
        args.append('--with-bvtinfo')
        args.append('--with-irack')
        args.append('{VENV}/tests/solar/bvt/')

    result = nosetests.delay(our_config, args, data)  # @UndefinedVariable
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


@app.route('/bvt/deviso', method='POST')
def bvt_deviso_post():
    """Handles requests from Dev team for user builds ISOs.
    """
    #BVTINFO_PROJECT_PATTERN = '(\D+)?(\d+\.\d+\.\d+)-?(hf\d+)?'
    SUITE_BVT = 'tests/bigiq/bvt/'
    SUITE_SMOKE = 'tests/solar/bvt/integration/filesystem/'
    CONFIG_FILE = 'config/suite_deviso_request.yaml'

    # For people who don't like to set the application/json header.
    data = json.load(bottle.request.body)
    #data = bottle.request.json

#    with IrackInterface(address=CONFIG.irack.address,
#                        timeout=30,
#                        username=CONFIG.irack.username,
#                        password=CONFIG.irack.apikey,
#                        ssl=False) as irack:
#        config_dir = os.path.dirname(CONFIG_FILE)
#        harness_files = [os.path.join(config_dir, x) for x in CONFIG.web.harnesses]
#        our_config = RCMD.irack.pick_best_harness(harness_files, ifc=irack)
    our_config = AttrDict(yaml.load(open(get_harness()).read()))

    # Prepare placeholders in our config
    our_config.update({'stages': {'main': {'setup': {'stage01-install-em': {'parameters': {}}}}}})
    our_config.update({'email': {'to': []}})

    # Append submitter's email to recipient list
    if data.get('email'):
        our_config.email.to.append(data['email'])
    our_config.email.to.extend(CONFIG.web.recipients)

    # Set version and build in the install stage
    params = our_config.stages.main.setup['stage01-install-em'].parameters
    params['custom iso'] = data['iso']

    args = []
    args[:] = NOSETESTS_ARGS

    args.append('--tc-file={VENV}/%s' % CONFIG_FILE)
    if data.get('debug'):
        args.append('--tc=stages._enabled:1')
        args.append('--no-email')
        tests = [os.path.join('{VENV}', x)
                for x in re.split('\s+', (data.get('tests') or SUITE_SMOKE).strip())]
        args.extend(tests)
    else:
        args.append('--tc=stages._enabled:1')
        args.append('--attr=status=CONFIRMED,priority=1')
        #args.append('--with-bvtinfo')
        args.append('--with-irack')
        args.append('{VENV}/%s' % SUITE_BVT)

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
    #options.clean = True
    options.no_sshkey = True
    if options.clean:
        options.selfip_internal = None
        options.selfip_external = None
        options.provision = None
        options.timezone = None

    result = confgen.delay(address=data.address, options=options, user_input=data)  # @UndefinedVariable
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
    options.product = 'em' if data.product == 'bigiq' else data.product
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

    result = install.delay(address=data.address, options=options, user_input=data)  # @UndefinedVariable
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

    result = ictester.delay(address=data.address, method=data.method,   # @UndefinedVariable
                            options=options,
                            params=data.arguments, user_input=data)

    #print arguments
    link = app.router.build('status', task_id=result.id)
    return dict(status=result.status, id=result.id, link=link)


if __name__ == '__main__':
    #app.run(host='0.0.0.0', server='gevent', port=PORT, debug=DEBUG)
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
