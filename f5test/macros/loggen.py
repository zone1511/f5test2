#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import sys
from f5test.utils.stb import RateLimit, TokenBucket
# from netaddr import IPAddress, ipv6_full

__version__ = '0.3'
LOG = logging.getLogger(__name__)
BOM = "\xEF\xBB\xBF"

CANNED_TYPES = {
#'rfc': dict(msg='Dummy RFC5242 message.',
#            structured_data=StructuredData([SDElement('exampleSDID@32473',
#                            [('iut','3'),
#                            ('eventSource','Application'),
#                            ('eventID','1011')]
#                            )])
#        ),
'rfc': (r'[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"][examplePriority@32473 class="high"] application event log entry...',
        r'[exampleSDID@32473 iut="3" eventSource="Application ăîâ" eventID="1011"][examplePriority@32473 class="high"] %ssome UTF8 stuff in the MSG %%: ionuţ ăîâ...' % BOM,
        ),
'asm': (r'ASM:unit_hostname="device00-{0}.test.net",management_ip_address="172.29.01.{0}",http_class_name="/Common/phpauction",web_application_name="/Common/phpauction",policy_name="/Common/phpauction",policy_apply_date="2014-05-22 02:23:06",violations="",support_id="1820138072675713393",request_status="passed",response_code="0",ip_client="192.168.184.191",route_domain="0",method="POST",protocol="HTTP",query_string="as=asd",x_forwarded_for_header_value="N/A",sig_ids="",sig_names="",date_time="2014-05-26 05:48:52",severity="Informational",attack_type="",geo_location="N/A",ip_address_intelligence="N/A",username="N/A",session_id="a08f7642929decd2",src_port="56699",dest_port="80",dest_ip="172.29.43.163",sub_violations="",virus_name="N/A",uri="/index.php",request="POST /index.php 2/1.4.2\r\nHost: 172.29.43.163\r\nAccept: */*\r\nContent-Length: 111\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\n",header="User-Agent: curl/7.19.7 (x86_64-redhat-linux-gnu) libcurl/7.19.7 NSS/3.14.0.0 zlib/1.2.3 libidn/1.18 libssh2/1.4.2\r\nHost: 172.29.43.163\r\nAccept: */*\r\nContent-Length: 111\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\n",response="Response logging disabled"',
        r'ASM:unit_hostname="device01-{0}.test.net",management_ip_address="172.29.02.{0}",http_class_name="/Common/forum{0:03}.com",web_application_name="/Common/forum{0:03}.com",policy_name="/Common/forum{0:03}.com",policy_apply_date="2014-04-13 01:12:{0:02}",violations="Illegal request length","Illegal URL length","Illegal file type",support_id="1123951646541139168{1}",request_status="blocked",response_code="0",ip_client="192.168.188.{0}",route_domain="{0}",method="GET",protocol="HTTP",query_string="",x_forwarded_for_header_value="N/A",sig_ids="",sig_names="",date_time="2014-05-12 08:37:45",severity="Critical",attack_type="Buffer Overflow","Forceful Browsing",geo_location="N/A",ip_address_intelligence="N/A",username="N/A",session_id="dee2bd97d2e48185",src_port="51516",dest_port="8084",dest_ip="172.29.43.{0}",sub_violations="",virus_name="N/A",uri="/",request="GET / HTTP/1.1\r\nHost: 172.29.43.{0}:8084\r\nConnection: keep-alive\r\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\r\nUser-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36\r\nAccept-Encoding: gzip,deflate,sdch\r\nAccept-Language: en-US,en;q=0.8\r\n\r\n",violation_details="BAD_MSG",header="Host: 172.29.43.{0}:8084\r\nConnection: keep-alive\r\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\r\nUser-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36\r\nAccept-Encoding: gzip,deflate,sdch\r\nAccept-Language: en-US,en;q=0.8\r\n\r\n",eventConversionDateTime="2014-05-12T08:38:{0:02}.949-07:00",additionalProperties="",response="Response logging disabled",generation=0,lastUpdateMicros=0',
        # r'ASM:unit_hostname="device91-{0}.test.net",management_ip_address="172.27.91.{0}",http_class_name="/Common/LTM91-217VIP-{0:03}",policy_name="LTM91-217VIP-{0:03}",policy_apply_date="2012-05-30 14:56:{0:02}",violations="",support_id="14860895721065583609",request_status="passed",response_code="200",ip_client="10.11.0.{0}",route_domain="{0}",method="GET",protocol="HTTP",query_string="",x_forwarded_for_header_value="N/A",sig_ids="",sig_names="",date_time="2012-06-07 12:14:{0:02}",severity="Informational",attack_type="",geo_location="N/A",ip_reputation="N/A",username="N/A",session_id="d08fd9631bbcbb59",src_port="440{0:02}",dest_port="80",dest_ip="10.11.104.{0}",sub_violations="",virus_name="N/A",uri="/1KB",request="GET /1KB HTTP/1.1\r\nConnection: Keep-Alive\r\nHost: 10.11.104.{0}\r\nUser-Agent: python/gevent-http-client-1.0a\r\n\r\n"',
        # r'ASM:unit_hostname="device91-{0}.test.net",management_ip_address="172.27.91.{0}",http_class_name="/Common/LTM91-217VIP-{0:03}",policy_name="LTM91-217VIP-{0:03}",policy_apply_date="2012-05-30 14:56:{0:02}",support_id="148608957210655836{1}",request_status="passed",response_code="200",ip_client="10.11.0.{0}",route_domain="{0}",method="POST",protocol="HTTP",query_string="a=1&b=123%123 ",x_forwarded_for_header_value="N/A",date_time="2012-06-07 12:14:{0:02}",severity="Critical",geo_location="N/A",ip_reputation="N/A",username="N/A",session_id="d08fd9631bbcbb59",src_port="440{0:02}",dest_port="80",dest_ip="10.11.104.{0}",virus_name="N/A",uri="/1KB",violations="violation{1},violation_common,violation{0}",attack_type="Detection Evasion,Path Traversal,super attack {0}",sub_violations="Evasion technique detected,some sub \rsub violation{0}",ip_list="1.1.1.{1},2.2.2.{0}"',
        # r'ASM:unit_hostname="device91-{0}.test.net",management_ip_address="172.27.91.{0}",http_class_name="/Common/LTM91-217VIP-{0:03}",policy_name="LTM91-217VIP-{0:03}",policy_apply_date="2012-05-30 14:56:{0:02}",violations="",support_id="14860895721065583609",request_status="passed",response_code="404",ip_client="10.11.0.{0}",route_domain="{0}",method="POST",protocol="HTTP",query_string="",x_forwarded_for_header_value="N/A",sig_ids="",sig_names="",date_time="2012-06-07 12:14:{0:02}",severity="Warning",attack_type="",geo_location="N/A",ip_reputation="N/A",username="N/A",session_id="d08fd9631bbcbb59",src_port="440{0:02}",dest_port="80",dest_ip="10.11.104.{0}",sub_violations="",virus_name="N/A",uri="/1KB",request="POST /1KB HTTP/1.1\r\nConnection: Close\r\nHost: 10.11.104.{0}\r\nUser-Agent: python/gevent-http-client-1.0a\r\n\r\n"',
        ),
'networkevent': (r'NetworkEvent: dvc="172.27.58.{0}",dvchost="bp11050-{0}.mgmt.pdsea.f5net.com",context_type="virtual",virtual_name="/Common/LTM58-{0}VIP-{0:03}",src_ip="10.10.0.{0}",dest_ip="10.10.1.{0}",src_port="80",dest_port="468{0:02}",ip_protocol="TCP",rule_name="",action="Closed",vlan="/Common/internal"',
                 r'NetworkEvent: dvc="172.27.58.{0}",dvchost="bp11050-{1}.mgmt.pdsea.f5net.com",context_type="virtual",virtual_name="/Common/LTM58-{0}VIP-{0:03}",src_ip="10.10.0.{0}",dest_ip="10.10.1.{0}",src_port="80",dest_port="468{0:02}",ip_protocol="TCP",rule_name="some rule",action="Open",vlan="/Common/external"',
                 ),
'avr': (r'AVR:Hostname="bp11050-177.mgmt.pdsea.f5net.com",Entity="ResponseCode",AVRProfileName="/Common/analytics",AggrInterval="300",EOCTimestamp="1341614700",HitCount="30",ApplicationName="",VSName="/Common/LTM58-177VIP-001",POOLIP="10.10.0.50",POOLIPRouteDomain="0",POOLPort="80",URL="/../../etc/passwd",ResponseCode="400",TPSMax="2885827072.000000",NULL,NULL,NULL,ServerLatencyMax="46476904",ServerLatencyTotal="16",ThroughputReqMax="11012",ThroughputReqTotal="3930",ThroughputRespMax="0",ThroughputRespTotal="61290"',
        r'AVR:Hostname="bp11050-177.mgmt.pdsea.f5net.com",Entity="Method",AVRProfileName="/Common/analytics",AggrInterval="300",EOCTimestamp="1341614700",HitCount="30",ApplicationName="",VSName="/Common/LTM58-177VIP-001",Method="2288208910"',
       ),
'dos3': (r'[F5@12276 action="Packet Dropped" hostname="nsoni-63.f5net.com" bigip_mgmt_ip="172.31.56.163" date_time="Aug 01 2012 06:48:09" dest_ip="10.10.10.163" dest_port="0" device_product="Network Firewall" device_vendor="F5" device_version="11.3.0.1607.0.58" dos_attack_event="Attack Sampled" dos_attack_id="565510146" dos_attack_name="Bad ICMP frame" errdefs_msgno="23003138" errdefs_msg_name="Network DoS Event" severity="8" partition_name="Common" route_domain="0" source_ip="10.10.10.166" source_port="0" vlan="/Common/internal"] "Aug 01 2012 06:48:09","172.31.56.163","nsoni-63.f5net.com","10.10.10.166","10.10.10.163","0","0","/Common/internal","Bad ICMP frame","565510146","Attack Sampled","Packet Dropped"',
         r'[F5@12276 action="None" hostname="nsoni-63.f5net.com" bigip_mgmt_ip="172.31.56.163" date_time="Aug 01 2012 06:50:36" dest_ip="" dest_port="" device_product="Network Firewall" device_vendor="F5" device_version="11.3.0.1607.0.58" dos_attack_event="Attack Stopped" dos_attack_id="0" dos_attack_name="Bad ICMP frame" errdefs_msgno="23003138" errdefs_msg_name="Network DoS Event" severity="8" partition_name="Common" route_domain="" source_ip="" source_port="" vlan=""] "Aug 01 2012 06:50:36","172.31.56.163","nsoni-63.f5net.com","","","","","","Bad ICMP frame","0","Attack Stopped","None"',
       ),
'dos7': (r'[F5@12276 action="Transparent" hostname="igor19.com" bigip_mgmt_ip="172.29.36.19" client_ip_geo_location="" client_request_uri="" configuration_date_time="Aug 23 2012 05:57:52" context_name="/Common/vs_228" context_type="Virtual Server" date_time="Aug 23 2012 05:58:12" device_product="ASM" device_vendor="F5" device_version="11.3.0" dos_attack_detection_mode="TPS Increased" dos_attack_event="Attack started" dos_attack_id="424172807" dos_attack_name="DOS L7 attack" dos_attack_tps="28" dos_dropped_requests_count="0" dos_mitigation_action="Source IP-Based Rate Limiting" errdefs_msgno="23003140" errdefs_msg_name="Application DoS Event" severity="7" partition_name="Common" profile_name="/Common/dos" source_ip=""]',
       ),

}


class LogGenerator(Macro):

    def __init__(self, options, address):
        self.options = Options(options)
        self.address = address

        super(LogGenerator, self).__init__()

    def setup(self):
        o = self.options

        assert self.address, "Invalid Address passed."
        assert o.port, "Please Provide a port."
        if not o.count:
            o.count = 1
        if not o.rate:
            o.rate = 1
        if not o.nofuzz:
            o.nofuzz = False

        klass = UDPSyslogEmitter if o.udp else TCPSyslogEmitter

        l = Logger(klass(address=(self.address, o.port),
                         octet_based_framing=False))

        if o.type:
            if 'CUSTOM' in o.type or 'custom' in o.type:
                if not o.custom:
                    o.custom = CANNED_TYPES['asm']
                CANNED_TYPES['custom'] = o.custom
            else:
                for x in o.type:
                    assert x in CANNED_TYPES, "Did not receive proper type of logs."
        if o.fromfile:
            # To Do: better arg check
            o.type = ['CUSTOM']
            x = []
            for filename in o.fromfile:
                if o.logasfile:
                    with open(filename) as f:
                        # probably some work required here when the case arrises
                        x += [f]
                else:
                    with open(filename) as f:
                        x += [line.strip() for line in f]
            CANNED_TYPES['custom'] = tuple(x)

        bucket = TokenBucket(3500, o.rate)
        rate_limiter = RateLimit(bucket)

        msgs = []
        full_size = 0
        full_byte_size = 0
        container_no_of_logs = 0
        for x in [CANNED_TYPES[x.lower()] for x in o.type]:
            msgs += x
            for i in x:
                full_size += len(i)
                full_byte_size += sys.getsizeof(i)
                container_no_of_logs += 1

        average_size = full_size / container_no_of_logs
        average_byte_size = full_byte_size / container_no_of_logs

        LOG.info("\nDoing this: \n"
                 "Remote Address/Port/Prot:       {0}:{1} ({2})\n"
                 "Type of logs sending:           {3}{4}{5}/{6}\n"
                 "Number of logs sending/rate:    {7} /{8}\n"
                 "Avg. size per log (ch/B):       {9}/{10}\n"
                 "No of detected unique events:   {11}\n"
                 "Sample of what is sending:      {12}\n"
                 "=======================================\n"
                 "In Progress...."
                 "\n"
                 .format(self.address, o.port, "TCP" if not o.udp else "UDP",
                         o.type, "/From File" if o.fromfile else "", "[" + str(len(o.fromfile)) + "]" if o.fromfile else "",
                         "Generating Fuzzy, Loop and Repeat." if not o.nofuzz else "Loop and Repeat As Is.",
                         o.count, o.rate,
                         average_size, average_byte_size,
                         container_no_of_logs,
                         (msgs[0]).format(0, 10) if not o.nofuzz else msgs[0]))

        now = time.time()
        rate_limiter(0, 1)
        for i in itertools.count():
            msg = msgs[i % len(msgs)]
            if not o.nofuzz:
                msg = msg.format(i % 10, 10 - i % 10)
            try:
                # LOG.info(msg)
                # LOG.info("\n:i:{0}".format(i))
                l.log(msg)
            except Exception, e:
                LOG.warning(e)
                time.sleep(1)

            if i + 1 == o.count:
                break
            rate_limiter(i, 100)
        delta = time.time() - now  # seconds
        bps = average_byte_size * o.count / delta
        LOG.info("f5.loggen: Stats:\n"
                 "Sent Events/time:   {0}/{1} seconds\n"
                 "Avg. events/sec:    {2} events/sec\n"
                 "Avg. Bytes/sec:     {3} Bytes/sec\n"
                 "Avg. KBytes/sec:    {4} KBytes/sec\n"
                 "Done...."
                 .format(o.count, delta,
                         o.count / delta,
                         bps,
                         bps / 1024))

        l.close()


def main():
    import optparse

    usage = """%prog [options] <address>
               Samples:
               Send 10 logs with rate 10 from file (each line is a log)
                   f5.loggen <address> -c 10 -r 10 -p 9025 -s -f "yourlogfile1.log" -f "yourlogfile2.log"
               Send 10 logs with rate 50 generated by the tool (defaults on asm)
                   f5.loggen <address> -c 10 -r 50 -p 9025
               Send 10 logs with rate 50 generated by the tool (rfc type)
                   f5.loggen <address> -c 10 -r 50 -p 9025 -t "rfc"
            """

    formatter = optparse.TitledHelpFormatter(indent_increment=2,
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="F5 Log Generator v%s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages")

    p.add_option("-c", "--count", metavar="INTEGER", default=1,
                 type="int", help="Number of entries. (default: 1)")
    p.add_option("-r", "--rate", metavar="INTEGER", default=1,
                 type="int", help="Rate limiter. low=1, medium=855, high=1000."
                 " (default: 1)")
    p.add_option("-u", "--udp", action="store_true",
                 help="Use UDP instead of TCP. (default: false)")
    p.add_option("-p", "--port", metavar="INTEGER", default=8514,
                 type="int", help="TCP/UDP port. (default: 8514)")
    p.add_option("-t", "--type", metavar="ENUM", action="append",
                 default=[],
                 help="Canned type of log entries to generate. Multiple "
                 "arguments accepted. Supported: RFC, ASM, NetworkEvent, AVR, DOS3, DOS7. "
                 "(default: ASM)")
    p.add_option("-C", "--custom", metavar="ENUM", action="append",
                 default=(),
                 help="Canned type of log entries already generated by you and passed here.")
    p.add_option("-s", "--nofuzz", metavar="BOOL", action="store_true",
                 default=False,
                 help="Set to True if you do not want the tool to autogenerate, "
                 "but send exactly what the file/custom fields have.")
    p.add_option("-f", "--fromfile", metavar="ENUM", action="append",
                 default=[],
                 help="Grab logs from list of files passed here. Eg. ['file1', 'file2']. "
                 "Unless this is a special file that has {0} in it, you must use with -s parameter.")
    p.add_option("-F", "--logasfile", metavar="BOOL", action="store_true",
                 default=False,
                 help="Used with --fromfile only if you want to send the whole"
                 " file as one single log. Not Tested.")

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
        options.type.append('asm')

    cs = LogGenerator(options=options, address=args[0])
    cs.run()


if __name__ == '__main__':
    main()
