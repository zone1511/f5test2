from __future__ import absolute_import
from nose.plugins.base import Plugin
#from nose.case import Test
#from nose.plugins.skip import SkipTest 
#from nose.result import TextTestResult
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from ..base import AttrDict
from ..utils.net import get_local_ip
import jinja2
import f5test.commands.icontrol as ICMD

__test__ = False

LOG = logging.getLogger(__name__)

DEFAULT_REPLY_TO = 'i.turturica@f5.com'
DEFAULT_FROM = 'em-selenium@f5.com'
MAIL_HOST = 'mail.f5net.com'

def _getattr(test, name, default):
    method = getattr(test.test, test.test._testMethodName)
    class_attr = getattr(test.test, name, default)
    return getattr(method, name, class_attr)
    

class Email(Plugin):

    enabled = True
    name = "email"
    score = 520

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
        from f5test.interfaces.config import ConfigInterface

        Plugin.configure(self, options, noseconfig)
        self.options = options
        if options.no_email or options.syncplan:
            self.enabled = False
        self.config_ifc = ConfigInterface()

    def afterTest(self, test):
        pass

#    def _get_duts_info(self):
#        # XXX: Should use lock=True, but the values are already cached. 
#        devices = self.config_ifc.get_device_discovers()
#        if not devices:
#            return
#        
#        info = []
#        for device in devices:
#            try:
#                platform = ICMD.system.get_platform(device=device)
#                version = ICMD.system.get_version(device=device, build=True)
#            except Exception, e:
#                LOG.error("%s: %s", type(e), e)
#                version = platform = 'failed'
#            info.append(AttrDict(device=device, platform=platform, 
#                                 version=version))
#        return info

    def _get_duts_info(self):
        # XXX: Should use lock=True, but the values are already cached. 
        devices = self.config_ifc.get_all_devices()
        if not devices:
            return
        
        info = []
        for device in devices:
            try:
                platform = ICMD.system.get_platform(device=device)
                version = ICMD.system.get_version(device=device, build=True)
            except Exception, e:
                LOG.error("%s: %s", type(e), e)
                version = platform = 'failed'
            info.append(AttrDict(device=device, platform=platform, 
                                 version=version))
        return info

    def _get_dut_info(self):
        # XXX: Should use lock=True, but the values are already cached.
        device = self.config_ifc.get_device()
        if not device:
            return
        
        info = AttrDict()
        try:
            info.platform = ICMD.system.get_platform(device=device)
            info.version = ICMD.system.get_version(device=device, build=True)
        except Exception, e:
            LOG.error("%s: %s", type(e), e)
            info.version = info.platform = 'failed'
        info.device = device
        return info

    def finalize(self, result):
        LOG.info("Sending email...")
        ctx = AttrDict()
        ctx.result = result
        ctx.config = self.config_ifc.open()
        ctx.duts = self._get_duts_info()
        ctx.dut = self._get_dut_info()
        ctx.test_runner_ip = get_local_ip(MAIL_HOST)
        ctx.sessionurl = self.config_ifc.get_session().get_url(ctx.test_runner_ip)

        headers = AttrDict()
        email = ctx.config.get('email', AttrDict())
        headers['From'] = email.get('from', DEFAULT_FROM)
        headers['To'] = email.get('to', DEFAULT_REPLY_TO)
        headers['Reply-To'] = email.get('reply-to', DEFAULT_REPLY_TO)
        
        env = jinja2.Environment(loader=jinja2.PackageLoader(__package__))
        if email.subject:
            template_subject = env.from_string(email.subject)
        else:
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
#        html = template_html.render(context)
        
        msg.attach(MIMEText(text, 'plain'))
        #msg.attach(MIMEText(html, 'html'))

        message = msg.as_string()
#        LOG.debug(text)

        server = None
        try:
            server = smtplib.SMTP(MAIL_HOST)
            server.sendmail(headers['From'], headers['To'], message)
            LOG.info("Sent!")
        except Exception, e:
            LOG.error("Sendmail failed: %s", e)
        finally:
            if server:
                server.quit()
