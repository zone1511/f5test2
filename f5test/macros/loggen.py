#!/usr/bin/env python
'''
Created on Jun 18, 2012

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
import logging
from loggerglue.emitter import TCPSyslogEmitter, UDPSyslogEmitter
from loggerglue.logger import Logger
import itertools
import time

__version__ = '0.1'
LOG = logging.getLogger(__name__)


CANNED_TYPES = {
#'rfc': dict(msg='Dummy RFC5242 message.',
#            structured_data=StructuredData([SDElement('exampleSDID@32473',
#                            [('iut','3'),
#                            ('eventSource','Application'),
#                            ('eventID','1011')]
#                            )])
#        ),
'rfc': (r'[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][examplePriority@32473 class="high"]',
        ),
'asm': (r'ASM:unit_hostname="device91-{0}.test.net",management_ip_address="172.27.91.{0}",http_class_name="/Common/LTM91-217VIP-{0:03}",policy_name="LTM91-217VIP-{0:03}",policy_apply_date="2012-05-30 14:56:{0:02}",violations="",support_id="14860895721065583609",request_status="passed",response_code="200",ip_client="10.11.0.{0}",route_domain="{0}",method="GET",protocol="HTTP",query_string="",x_forwarded_for_header_value="N/A",sig_ids="",sig_names="",date_time="2012-06-07 12:14:{0:02}",severity="Informational",attack_type="",geo_location="N/A",ip_reputation="N/A",username="N/A",session_id="d08fd9631bbcbb59",src_port="440{0:02}",dest_port="80",dest_ip="10.11.104.{0}",sub_violations="",virus_name="N/A",uri="/1KB",request="GET /1KB HTTP/1.1\r\nConnection: Keep-Alive\r\nHost: 10.11.104.{0}\r\nUser-Agent: python/gevent-http-client-1.0a\r\n\r\n"',
        r'ASM:unit_hostname="device91-{0}.test.net",management_ip_address="172.27.91.{0}",http_class_name="/Common/LTM91-217VIP-{0:03}",policy_name="LTM91-217VIP-{0:03}",policy_apply_date="2012-05-30 14:56:{0:02}",support_id="148608957210655836{1}",request_status="passed",response_code="200",ip_client="10.11.0.{0}",route_domain="{0}",method="POST",protocol="HTTP",query_string="a=1&b=123%123 ",x_forwarded_for_header_value="N/A",date_time="2012-06-07 12:14:{0:02}",severity="Critical",geo_location="N/A",ip_reputation="N/A",username="N/A",session_id="d08fd9631bbcbb59",src_port="440{0:02}",dest_port="80",dest_ip="10.11.104.{0}",virus_name="N/A",uri="/1KB",violations="violation{1},violation_common,violation{0}",attack_type="Detection Evasion,Path Traversal,super attack {0}",sub_violations="Evasion technique detected,some sub \rsub violation{0}",ip_list="1.1.1.{1},2.2.2.{0}"',
        ),
'networkevent': (r'NetworkEvent: dvc="172.27.58.{0}",dvchost="bp11050-{0}.mgmt.pdsea.f5net.com",context_type="virtual",virtual_name="/Common/LTM58-{0}VIP-{0:03}",src_ip="10.10.0.{0}",dest_ip="10.10.1.{0}",src_port="80",dest_port="468{0:02}",ip_protocol="TCP",rule_name="",action="Closed",vlan="/Common/internal"',
                 r'NetworkEvent: dvc="172.27.58.{0}",dvchost="bp11050-{1}.mgmt.pdsea.f5net.com",context_type="virtual",virtual_name="/Common/LTM58-{0}VIP-{0:03}",src_ip="10.10.0.{0}",dest_ip="10.10.1.{0}",src_port="80",dest_port="468{0:02}",ip_protocol="TCP",rule_name="some rule",action="Open",vlan="/Common/external"',
                 ),
'avr': (r'AVR:Hostname="bp11050-177.mgmt.pdsea.f5net.com",Entity="ResponseCode",AVRProfileName="/Common/analytics",AggrInterval="300",EOCTimestamp="1341614700",HitCount="30",ApplicationName="",VSName="/Common/LTM58-177VIP-001",POOLIP="10.10.0.50",POOLIPRouteDomain="0",POOLPort="80",URL="/../../etc/passwd",ResponseCode="400",TPSMax="2885827072.000000",NULL,NULL,NULL,ServerLatencyMax="46476904",ServerLatencyTotal="16",ThroughputReqMax="11012",ThroughputReqTotal="3930",ThroughputRespMax="0",ThroughputRespTotal="61290"'
        r'AVR:Hostname="bp11050-177.mgmt.pdsea.f5net.com",Entity="Method",AVRProfileName="/Common/analytics",AggrInterval="300",EOCTimestamp="1341614700",HitCount="30",ApplicationName="",VSName="/Common/LTM58-177VIP-001",Method="2288208910"'
       )
}


class LogGenerator(Macro):

    def __init__(self, options, address):
        self.options = Options(options.__dict__)
        self.address = address

        super(LogGenerator, self).__init__()

    def setup(self):
        o = self.options

        klass = UDPSyslogEmitter if o.udp else TCPSyslogEmitter

        l = Logger(klass(address=(self.address, o.port),
                         octet_based_framing=False))

        assert o.type
        n = len(o.type)
        for i in itertools.count():
            msgs = CANNED_TYPES[o.type[i % n].lower()]
            msg = msgs[i % len(msgs)]
            try:
                l.log(msg.format(i % 10, 10 - i % 10))
            except Exception, e:
                LOG.warning(e)
                time.sleep(1)
            #print msg
            if i + 1 == o.count:
                break
            time.sleep(o.interval)

        l.close()


def main():
    import optparse
    import sys

    usage = """%prog [options] <address>"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2,
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="F5 Log Generator v%s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages")

    p.add_option("-c", "--count", metavar="INTEGER", default=1,
                 type="int", help="Number of entries. (default: 1)")
    p.add_option("-i", "--interval", metavar="INTEGER", default=0.1,
                 type="float", help="Interval. (default: 0.1 secs)")
    p.add_option("-u", "--udp", action="store_true",
                 help="Use UDP instead of TCP. (default: false)")
    p.add_option("-p", "--port", metavar="INTEGER", default=8514,
                 type="int", help="TCP/UDP port. (default: 8514)")
    p.add_option("-t", "--type", metavar="ENUM", action="append",
                 default=[],
                 help="Canned type of log entries to generate. Multiple "
                 "arguments accepted. Supported: RFC, ASM, NetworkEvent, AVR. "
                 "(default: RFC)")

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        logging.getLogger('f5test').setLevel(logging.INFO)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)

    if not args:
        p.print_version()
        p.print_help()
        sys.exit(2)

    if not options.type:
        options.type.append('rfc')

    cs = LogGenerator(options=options, address=args[0])
    cs.run()


if __name__ == '__main__':
    main()
