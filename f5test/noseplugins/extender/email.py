'''
Created on Aug 29, 2014

@author: jono
'''
from __future__ import absolute_import

import copy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import re
import smtplib

import jinja2

from ...base import AttrDict
from ...utils.progress_bar import ProgressBar
from . import ExtendedPlugin, PLUGIN_NAME


LOG = logging.getLogger(__name__)
DEFAULT_FROM = 'em-selenium@f5.com'
DEFAULT_SUBJECT = 'Test Run'
MAIL_HOST = 'mail.f5net.com'
DUMP_EMAIL_FILENAME = 'email.html'


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

    links = {'((?:BZ|BUG)\s*(\d{6}))':
             r"<a href='http://bugzilla.olympus.f5net.com/show_bug.cgi?id=\2'>\1</a>",
             '((?:OT|ONTIME)\s*(\d{4,}))':
             r"<a href='https://f5networks.ontimenow.com/viewitem.aspx?id=\2&type=features&force_use_number=false'>\1</a>"}
    result = string
    for expr, href in links.items():
        result = re.sub(expr, href, result, flags=re.IGNORECASE)
    return result if result == string else jinja2.filters.do_mark_safe(result)


def customfilter_product(duts, product='bigip'):
    if duts is None or isinstance(duts, jinja2.Undefined) or\
            not isinstance(duts, list) or not isinstance(product, basestring):
        return duts

    result = list()
    for dut in duts:
        if dut.version.product.product == product:
            result.append(dut)

    return result


class Email(ExtendedPlugin):
    """
    Send email report.
    """
    enabled = True

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--with-email', action='store_true',
                          dest='with_email', default=False,
                          help="Enable Email reporting. (default: no)")
        parser.add_option('--with-email-subject', action="store",
                          dest='with_email_subject',
                          help="Change Email subject. (default: 'Test Run')")

    def configure(self, options, noseconfig):
        super(Email, self).configure(options, noseconfig)
        from ...interfaces.testcase import ContextHelper
        self.data = ContextHelper().set_container(PLUGIN_NAME)
        self.enabled = noseconfig.options.with_email

        if self.enabled and noseconfig.options.collect_only:
            LOG.warn('Email reporting not supported in --collect-only mode.')
            self.enabled = False

    def make_bars(self):
        self.data.result.bars = {}
        b = self.data.result.bars
        result = self.data.test_result
        b.good = ProgressBar(result.testsRun, result.testsRun
                             - result.failCount()
                             - result.notFailCount())
        b.bad = ProgressBar(result.testsRun, result.failCount())
        b.unknown = ProgressBar(result.testsRun, result.notFailCount())
        b.ki = ProgressBar(result.testsRun, len(result.known_issue))

        # New progress bars for when Skipped tests should be ignored.
        b.good_no_skips = ProgressBar(result.testsRun
                                      - result.notFailCount(),
                                      result.testsRun
                                      - result.failCount()
                                      - result.notFailCount())
        b.bad_no_skips = ProgressBar(result.testsRun
                                     - result.notFailCount(),
                                     result.failCount())

        x = {}
        for label, storage in result.blocked.items():
            for truple in storage:
                test, err, context = truple
                y = x.setdefault(label, {})
                z = y.setdefault(context, [])
                z.append((test, err))
        self.data.result.blocked_groups = x

    def compile_emails(self):
        base = self.options
        recipients = []
        specs = base.multi if base.multi else [base]

        for spec in specs:
            tmp = copy.copy(base)
            tmp.update(spec)
            spec = tmp
            if self.noseconfig.options.with_email_subject:
                spec.subject = self.noseconfig.options.with_email_subject
            elif self.data.config.testrun.description:
                spec.subject = self.data.config.testrun.description
            else:
                spec.subject = spec.get('subject', DEFAULT_SUBJECT)
            headers = AttrDict()
            if not spec:
                LOG.warning('Email plugin not configured.')
                return
            headers['From'] = spec.get('from', DEFAULT_FROM)
            if isinstance(spec.get('to', []), basestring):
                recipients = set([spec.to])
            else:
                recipients = set(spec.to)

            if self.data.config.testrun.owner:
                recipients.add(self.data.config.testrun.owner)
                headers['From'] = self.data.config.testrun.owner
                headers['Sender'] = DEFAULT_FROM

            assert recipients, "Please set the email section in the config file."
            if spec.get('reply-to'):
                headers['Reply-To'] = spec['reply-to']
            else:
                if self.data.config.testrun.owner:
                    headers['Reply-To'] = self.data.config.testrun.owner

            if spec.get('templates'):
                config_dir = os.path.dirname(self.data.config._filename)
                templates_dir = os.path.join(config_dir, spec.templates)
                loader = jinja2.FileSystemLoader(templates_dir)
            else:
                loader = jinja2.PackageLoader(__package__)
            env = jinja2.Environment(loader=loader, autoescape=True)

            # Add custom filters
            env.filters['ljust'] = customfilter_ljust
            env.filters['rjust'] = customfilter_rjust
            env.filters['bzify'] = customfilter_bzify
            env.filters['product'] = customfilter_product

            template_subject = env.get_template('email_subject.tmpl')
            headers['Subject'] = template_subject.render(self.data, spec=spec)
            headers['To'] = list(recipients)

            if int(self.data.result.bars.good_no_skips.percent_done) == 0:
                headers['Importance'] = 'high'

            msg = MIMEMultipart('alternative')
            for key, value in headers.items():
                if isinstance(value, (tuple, list)):
                    value = ','.join(value)
                msg.add_header(key, value)

            template_html = env.get_template('email_html.tmpl')

            html = template_html.render(self.data)

            msg.attach(MIMEText(html, 'html'))

            message = msg.as_string()
            yield AttrDict(headers=headers, body=message, text=html)

    def dump_text(self, email):
        path = self.data.session.path
        if os.path.exists(path):
            with open(os.path.join(path, DUMP_EMAIL_FILENAME), 'wt') as f:
                f.write(email.text)

    def finalize(self, result):
        self.make_bars()
        mail_host = self.data.get('server', MAIL_HOST)
        emails = self.compile_emails()

        server = None
        try:
            server = smtplib.SMTP(mail_host)
            for email in emails:
                server.sendmail(email.headers['From'], email.headers['To'],
                                email.body)
                LOG.info("Email report sent to: %s", email.headers['To'])
            # Dump the text version of the last email template
            self.dump_text(email)
        except Exception, e:
            LOG.error('Email report failed: %s', e)
            raise
        finally:
            if server:
                server.quit()
