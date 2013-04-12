from __future__ import absolute_import
from nose.plugins.base import Plugin
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from ..base import AttrDict
from ..utils import Version
from ..utils.net import get_local_ip
from ..utils.progress_bar import ProgressBar
import jinja2
import os
import re
import copy

__test__ = False

LOG = logging.getLogger(__name__)

DEFAULT_FROM = 'em-selenium@f5.com'
MAIL_HOST = 'mail.f5net.com'


def _getattr(test, name, default):
    method = getattr(test.test, test.test._testMethodName)
    class_attr = getattr(test.test, name, default)
    return getattr(method, name, class_attr)


def customfilter_ljust(string, width, fillchar=' '):
    if string is None or isinstance(string, jinja2.Undefined):
        return string

    return string.ljust(width, fillchar)


def customfilter_rjust(string, width, fillchar=' '):
    if string is None or isinstance(string, jinja2.Undefined):
        return string

    return string.rjust(width, fillchar)


def customfilter_bzify(string):
    if string is None or isinstance(string, jinja2.Undefined):
        return string

    link = r"<a href='http://bugzilla.olympus.f5net.com/show_bug.cgi?id=\2'>\1</a>"
    return re.sub('((?:BZ|BUG)\s*(\d{6}))', link, string, flags=re.IGNORECASE)


class Email(Plugin):
    """
    Email plugin. Enabled by default. Disable with ``--no-email``. This plugin
    sends an email report at the end of a test run. Uses Jinja2 as the template
    language.
    """
    enabled = True
    name = "email"
    score = 517

    def options(self, parser, env):
        """Register commandline options.
        """
#        Plugin.options(self, parser, env)
        parser.add_option('--no-email', action='store_true',
                          dest='no_email', default=False,
                          help="Disable email reporting. (default: no)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        from ..interfaces.config import ConfigInterface
        import f5test.commands.icontrol as ICMD

        Plugin.configure(self, options, noseconfig)
        self.options = options
        self.noseconfig = noseconfig
        if options.no_email or options.syncplan:
            self.enabled = False
        self.config_ifc = ConfigInterface()
        self.ICMD = ICMD

    def afterTest(self, test):
        pass

    def _get_duts_info(self):
        devices = self.config_ifc.get_all_devices()
        if not devices:
            return

        ret = []
        for device in devices:
            info = AttrDict()
            info.device = device
            try:
                info.platform = self.ICMD.system.get_platform(device=device)
                info.version = self.ICMD.system.get_version(device=device)
                v = self.ICMD.system.parse_version_file(device=device)
                info.project = v.get('project', '')
                info.edition = v.get('edition', '')
            except Exception, e:
                LOG.error("%s: %s", type(e), e)
                info.version = Version()
                info.platform = ''
            ret.append(info)
        return ret

    def _get_dut_info(self):
        device = self.config_ifc.get_device()
        if not device:
            return

        info = AttrDict()
        try:
            info.platform = self.ICMD.system.get_platform(device=device)
            info.version = self.ICMD.system.get_version(device=device)
            v = self.ICMD.system.parse_version_file(device=device)
            info.project = v.get('project', '')
            info.edition = v.get('edition', '')
        except Exception, e:
            LOG.error("%s: %s", type(e), e)
            info.version = Version()
            info.platform = ''
        info.device = device
        return info

    def _set_bars(self, result, ctx):
        ctx.bars = {}
        ctx.bars.good = ProgressBar(result.testsRun, result.testsRun
                                                     - len(result.failures)
                                                     - len(result.errors)
                                                     - len(result.skipped))
        ctx.bars.bad = ProgressBar(result.testsRun, len(result.failures)
                                                    + len(result.errors))
        ctx.bars.unknown = ProgressBar(result.testsRun, len(result.skipped))

        # New progress bars for when Skipped tests should be ignored.
        ctx.bars.good_no_skips = ProgressBar(result.testsRun
                                             - len(result.skipped),
                                             result.testsRun
                                             - len(result.failures)
                                             - len(result.errors)
                                             - len(result.skipped))
        ctx.bars.bad_no_skips = ProgressBar(result.testsRun
                                            - len(result.skipped),
                                            len(result.failures)
                                            + len(result.errors))

    def make_emails(self, ctx):
        base = ctx.config.get('email', AttrDict())
        specs = base.multi if base.multi else [base]

        for spec in specs:
            tmp = copy.copy(base)
            tmp.update(spec)
            spec = tmp
            ctx.email = spec
            headers = AttrDict()
            if not spec:
                LOG.warning('Email plugin not configured.')
                return
            headers['From'] = spec.get('from', DEFAULT_FROM)
            headers['To'] = spec.get('to')
            assert headers['To'], "Please set the email section in the config file."
            if spec.get('reply-to'):
                headers['Reply-To'] = spec['reply-to']

            if spec.get('templates'):
                config_dir = os.path.dirname(ctx.config._filename)
                templates_dir = os.path.join(config_dir, spec.templates)
                loader = jinja2.FileSystemLoader(templates_dir)
            else:
                loader = jinja2.PackageLoader(__package__)
            env = jinja2.Environment(loader=loader, autoescape=True)

            # Add custom filters
            env.filters['ljust'] = customfilter_ljust
            env.filters['rjust'] = customfilter_rjust
            env.filters['bzify'] = customfilter_bzify

            template_subject = env.get_template('email_subject.tmpl')
            headers['Subject'] = template_subject.render(ctx)

            msg = MIMEMultipart('alternative')
            for key, value in headers.items():
                if isinstance(value, (tuple, list)):
                    value = ','.join(value)
                msg.add_header(key, value)

            template_text = env.get_template('email_text.tmpl')
            template_html = env.get_template('email_html.tmpl')

            text = template_text.render(ctx)
            html = template_html.render(ctx)

            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))

            message = msg.as_string()
            yield AttrDict(headers=headers, body=message)

    def finalize(self, result):
        from ..interfaces.testcase import ContextHelper
        LOG.info("Sending email...")
        global_context = ContextHelper('__main__')
        ctx = AttrDict()
        ctx.result = result
        ctx.config = self.config_ifc.open()
        ctx.noseconfig = self.noseconfig
        ctx.data = global_context.get_container('email')
        ctx.duts = self._get_duts_info()
        ctx.dut = self._get_dut_info()
        ctx.test_runner_ip = get_local_ip(MAIL_HOST)
        ctx.sessionurl = self.config_ifc.get_session().get_url(ctx.test_runner_ip)
        ctx.testtime = global_context.get_container('testtime')
        self._set_bars(result, ctx)

        emails = self.make_emails(ctx)

        server = None
        try:
            server = smtplib.SMTP(MAIL_HOST)
            for email in emails:
                server.sendmail(email.headers['From'], email.headers['To'],
                                email.body)
                LOG.info("Sent!")
        except Exception, e:
            LOG.error("Sendmail failed: %s", e)
        finally:
            if server:
                server.quit()
