from nose.plugins.base import Plugin
from nose.case import Test
from nose.plugins.skip import SkipTest 
from nose.util import isclass
from nose.suite import ContextSuite
from ..utils.net import get_local_ip
import logging
from ..base import AttrDict

__test__ = False

LOG = logging.getLogger(__name__)

DIRTY_ATTR = '_dirty_'
PLATFORM_TO_ENV = {'C106': 'EM4000',
                   'D38':  'EM3000',
                   'C36':  'EM500',
                   'Z100': 'EMVirtualMachine'}

STATUS_ID_TEXT = {1: 'PROPOSED',
                  2: 'CONFIRMED',
                  3: 'DISABLED'}

def _getattr(test, name, default):
    method = getattr(test.test, test.test._testMethodName)
    class_attr = getattr(test.test, name, default)
    return getattr(method, name, class_attr)
    
def secs_to_str(seconds):
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return "%s:%s:%s" % (hours, mins, secs)

class Testopia(Plugin):

    enabled = False
    name = "testopia"
    score = 518

    def options(self, parser, env):
        """Register commandline options.
        """
        parser.add_option('--testopia-section', action='store', dest='section',
                          default='testopia', metavar="SECTION",
                          help="The name of the testopia section in the config.")
        parser.add_option('--testopia-testrun-summary', action='store', 
                          dest='testrun_summary',
                          default='Automated run %(session)s', metavar="SECTION",
                          help="The name of the TestRun. (default: Automated run %(session)s)")
        parser.add_option('--testopia-syncplan', action='store_true',
                          dest='syncplan', default=False,
                          help="Sync the testplan with the test collection. ")
        parser.add_option('--testopia-remove-cases', action='store_true',
                          dest='remove_cases', default=False,
                          help="Used together with syncplan option. When "
                          "TestCases are present in Testopia but not on disk, "
                          "delete them from Testopia. (default: no)")
        parser.add_option('--with-testopia', action='store_true',
                          dest='with_testopia', default=False,
                          help="Enable testopia. (default: no)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        from f5test.interfaces.testopia import TestopiaInterface
        from f5test.interfaces.config import ConfigInterface
        import f5test.commands.icontrol as ICMD
        import f5test.commands.testopia as TCMD

        Plugin.configure(self, options, noseconfig)
        self.options = options
        #self._parse_attr(options)

        if options.with_testopia or options.syncplan:
            self.enabled = True

        self.testopia_ifc = TestopiaInterface()
        self.config_ifc = ConfigInterface()
        self.ICMD = ICMD
        self.TCMD = TCMD
        self.product = 'Enterprise Manager'
        self.tcs = {}
        self.tcs_ran = set()

    def startContext(self, context):
        if self.options.syncplan:
            if isclass(context):
                names = ContextSuite.classSetup + ContextSuite.classTeardown
            else:
                names = ContextSuite.moduleSetup + ContextSuite.moduleTeardown
                if hasattr(context, '__path__'):
                    names += ContextSuite.packageSetup + ContextSuite.packageTeardown
            # If my context has any fixture attribute, I have fixtures
            for m in names:
                if hasattr(context, m):
                    setattr(context, m, None)
        
    def _update_tc_if_needed(self, t, adr, test):
        status = _getattr(test, 'status', 'CONFIRMED')
        product = _getattr(test, 'product', self.product)
        category = _getattr(test, 'category', 'Functional')
        priority = _getattr(test, 'priority', 1)
        is_dirty = bool(_getattr(test, DIRTY_ATTR, False))
        components = []
        for component in _getattr(test, 'components', ''):
            components.append(dict(product=product, component=component))
        tags = _getattr(test, 'tags', '')
        requirement = _getattr(test, 'requirement', '')
        author = _getattr(test, 'author', '')
        summary = adr
        action = test.test._testMethodDoc or ''
        estimated_time = secs_to_str(_getattr(test, 'duration', 0))

        tc = self.tcs[adr]
        
        if (tc['script'] != adr or
            tc['priority_id'] != priority or
            is_dirty):
            LOG.info('Updating %d: %s', tc['case_id'], adr)

            tc_tags = t.TestCase.get_tags(tc['case_id'])
            for tag in set(map(str.lower, tc_tags)) - set(map(str.lower, tags)):
                LOG.info('Removing tag: "%s..."', tag)
                t.TestCase.remove_tag(tc['case_id'], tag)
            to_add = list(set(map(str.lower, tags)) - set(map(str.lower, tc_tags)))
            if to_add:
                LOG.info('Adding tags: %s...', to_add)
                t.TestCase.add_tag(tc['case_id'], to_add)

            tc_components = t.TestCase.get_components(tc['case_id'])
            LOG.info('Removing all components...')
            for component in tc_components:
                t.TestCase.remove_component(tc['case_id'], component['id'])

            LOG.info('Adding components...')
            t.TestCase.add_component(tc['case_id'], components)

            LOG.info('Updating text...')
            ret = t.TestCase.get_text(tc['case_id'])
            if ret['action'] != action:
                t.TestCase.store_text(tc['case_id'], action, '', '', '')

            LOG.info('Updating TestCase fields...')
            ret = t.TestCase.update(tc['case_id'],
                                    dict(status=status,
                                         category={'product': product,
                                                   'category': category},
                                         priority=priority,
                                         summary=summary.strip(),
                                         action=action.strip().replace('\n', '<br>'),
                                         requirement=requirement,
                                         estimated_time=estimated_time,
                                         default_tester=author,
                                         script=adr,
                                         ))
            LOG.debug('TestCase update: %s', ret)

    def prepareTestCase(self, test):
        """If enumerate option is set, add testcases to test plan specified in
        config.testopia.test plan
        """
        filename, module, method = test.address()
        adr = "%s:%s" % (module, method)
        tc = self.tcs.get(adr)
        

        if not self.options.syncplan:
            if tc and STATUS_ID_TEXT[tc['case_status_id']] != 'CONFIRMED':
                LOG.warn('Skip: %s testopia status is not CONFIRMED' % adr)
                return lambda x:x
            return
        
        if method is None:
            LOG.warn('cannot load %s', filename)
        else:
            c = self.config_ifc.open().get(self.options.section)
            t = self.testopia_ifc.open()
            bits = (test.test._testMethodDoc or adr).split('\n', 1)
            action = ''
            
            if len(bits) > 1:
                summary, action = bits
            elif len(bits) == 1:
                summary = bits[0]
            else:
                summary = adr
            # WARNING: always use the address as the summary
            #===================================================================
            summary = adr
            action = test.test._testMethodDoc or ''
            #===================================================================
            LOG.info('found: %s', adr)
            
            if adr in self.tcs:
                self._update_tc_if_needed(t, adr, test)
                self.tcs.pop(adr)
                return lambda x:x
            
            # Defaults for new test cases.
            status = _getattr(test, 'status', 'CONFIRMED')
            product = _getattr(test, 'product', self.product)
            category = _getattr(test, 'category', 'Functional')
            priority = _getattr(test, 'priority', 1)
            components = []
            for component in _getattr(test, 'components', ''):
                components.append(dict(product=product, component=component))
            tags = _getattr(test, 'tags', '')
            requirement = _getattr(test, 'requirement', '')
            author = _getattr(test, 'author', '')
            estimated_time = secs_to_str(_getattr(test, 'duration', 0))
            plan_id = c.get('testplan')

            ret = t.TestCase.create(dict(status=status,
                                         category={'product': product,
                                                   'category': category},
                                         priority=priority,
                                         summary=summary.strip(),
                                         action=action.strip().replace('\n', '<br>'),
                                         components=components,
                                         requirement=requirement,
                                         tags=tags,
                                         default_tester=author,
                                         estimated_time=estimated_time,
                                         script=adr,
                                         isautomated=True,
                                         plans=plan_id
                                         ))
            
            if isinstance(ret, list) and ret[0].get('ERROR'):
                LOG.error("Failed: %s:%s", ret[0]['ERROR']['_faultcode'], 
                                           ret[0]['ERROR']['_faultstring'])
            else:
                LOG.info("TestCase created: %d", ret['case_id'])
    
        return lambda x:x

    def _render_notes(self):
        note = ""
        dut = self.config_ifc.get_device()
        my_ip = get_local_ip(dut.address)
        note += "Test runner: %s\n" \
                "DUT (%s): %s\n\n" % (my_ip, dut.alias, dut.address)
        
        for device in self.config_ifc.get_all_devices():
            note += "%s: %s\n" % (device.alias, device.address)
        
        config = self.config_ifc.open()
        if config.paths:
            sessionurl = self.config_ifc.get_session().get_url(my_ip)
            note += "Debug logs: %s\n" % sessionurl

        return note
        
    def _set_tcs(self):
        c = self.config_ifc.open().get(self.options.section)
        t = self.testopia_ifc.open()
        
        LOG.debug('Receiving testcase list...')
        plan_id = c.get('testplan')
        ret = t.TestCase.list(dict(plan_id=plan_id, isautomated=True, viewall=1))
        
        # Setup the address -> ID mapping
        for tc in ret:
            self.tcs[tc['script']] = tc
        c._tcs = self.tcs
        LOG.info('Found: %d TestCases in TestPlan %d', len(self.tcs), plan_id)

    def begin(self):
        """Create a new TestRun and add all TCs.
        """
        self._set_tcs()
        if self.options.syncplan:
            return

        # This is the first time we try to connect to DUT. We don't know if it
        # has the correct password set or not, so we're resetting it now.
        LOG.debug('Re-setting password on DUT...')
        try:
            assert self.ICMD.system.set_password()
        except:
            LOG.error('Could not reset password on DUT. Giving up.')
            return
        
        config = self.config_ifc.open()
        c = config.get(self.options.section)
        t = self.testopia_ifc.open()

        LOG.debug('Creating a new build (if needed)...')
        version = self.ICMD.system.get_version(build=True)
        v_str = "%s %s" % (version.version, version.build)
        ret = self.TCMD.build.create_build(v_str, c.product)
        c._build = ret['build_id']
        LOG.debug('Build id: %d', c._build)

        LOG.debug('Create a new testrun...')
        platform = self.ICMD.system.get_platform()
        environment = PLATFORM_TO_ENV[platform]
        
        ret = t.Environment.check_environment(environment, c.product)
        c._environment = ret['environment_id']
        LOG.debug('Environment id: %d', c._environment)
        
        ctx = AttrDict()
        ctx.session = self.config_ifc.get_session().name
        summary = self.options.testrun_summary % ctx or ''
        notes = self._render_notes()
        case_ids = [x['case_id'] for x in self.tcs.values()]
        ret = t.TestRun.create(dict(plan_id=c.testplan,
                                    environment=c._environment,
                                    build=c._build,
                                    manager=c.username,
                                    summary=summary,
                                    notes=notes,
                                    cases=case_ids))
        c._testrun = ret['run_id']
        LOG.debug('Run: %d', c._testrun)
        if c.output and c.output.tags:
            LOG.debug('Adding tags to testrun...')
            ret = t.TestRun.add_tag(c._testrun, c.output.tags)

    def _flip_testcase(self, test, status, notes=''):
        if isinstance(test, Test):
            _, module, method = test.address()
            adr = "%s:%s" % (module, method)
            tc = self.tcs.get(adr)
            LOG.debug(self.tcs.get(adr))
        elif isinstance(test, basestring):
            adr = test
            tc = self.tcs.get(test)
        else:
            return

        if not tc:
            LOG.error('%s is not in the testplan!', adr)
            return
        
        case_id = tc['case_id']
        t = self.testopia_ifc.open()
        c = self.config_ifc.open().get(self.options.section)
        LOG.debug('Flipping tescase %d to %s', case_id, status)
        if c._testrun:
            try:
                t.TestCaseRun.update(c._testrun, case_id, c._build, c._environment,
                                     dict(status=status,
                                          notes=str(notes)))
            except:
                LOG.error("Testopia failed to update TC: %s", case_id)
        self.tcs_ran.add(case_id)

    def handleFailure(self, test, err):
        """Flip TestCaseRun from idle to failed."""
        self._flip_testcase(test, 'FAILED', err[1])

    def addError(self, test, err):
        if issubclass(SkipTest, err[0]):
            self._flip_testcase(test, 'PAUSED', err[1])
        else:
            #self._flip_testcase(test, 'ERROR', err[1])
            self._flip_testcase(test, 'FAILED', err[1])

    def addSuccess(self, test):
        """Flip TestCaseRun from idle to success."""
        self._flip_testcase(test, 'PASSED')

    def finalize(self, result):
        """Close TestRun and flip all untouched TCs to blocked.
        """
        c = self.config_ifc.open().get(self.options.section)
        t = self.testopia_ifc.open()

        case_ids = dict(((x['case_id'], x['script']) for x in self.tcs.values()))
        if self.options.syncplan:
            if self.options.remove_cases:
                LOG.warn('Removing %s from Testopia!', case_ids)
                plan_id = c.get('testplan')
                for case_id in case_ids:
                    LOG.info('Unlinking case_id: %s', case_id)
                    t.TestCase.unlink_plan(case_id, plan_id)
            return

        tcs = [str(x) for x in set(case_ids) - self.tcs_ran]
        if tcs:
            ret = t.TestCaseRun.list(dict(run_id=c._testrun,
                                          case_id=",".join(tcs),
                                          build_id=c._build,
                                          environment_id=c._environment
                                          ))
            cr_ids = [x['case_run_id'] for x in ret]
            #LOG.warn('Flipping to PAUSED %d tests', len(cr_ids))
            LOG.warn('%d tests not ran', len(cr_ids))
            #ret = t.TestCaseRun.delete(cr_ids)
            #LOG.info(ret)
    
            #t.TestCaseRun.update(cr_ids, dict(status='PAUSED'))
        if c._testrun:
            LOG.debug('Closing testrun: %d', c._testrun)
            t.TestRun.update(c._testrun, dict(status='STOPPED'))

#        if result.testsRun != len(self.tcs):
#            LOG.warn("TestPlan %d not in sync: ran=%d planned=%d", 
#                      c.get('testplan'), result.testsRun, len(self.tcs))
            
