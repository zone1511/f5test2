from IPy import IP
from socket import socket, gethostbyname_ex, SOCK_DGRAM, AF_INET

BASE_IPV6 = 'FD32:00F5:0000::'

def resolv(hostname):
    """Only IPv4 support for now"""
    _, _, ip_list = gethostbyname_ex(hostname)
    return ip_list[0]

def get_local_ip(peer):
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect((peer.split(':', 1)[0], 0))
    ip = s.getsockname()[0]
    s.close()
    return ip

def ip4to6(address, base=BASE_IPV6):
    """
    Convert an IPv4 to IPv6 by splitting the network part of the ip and shifting
    it to the Global ID and Subnet ID zone.
    
    @param address: IPv4 address (e.g. '172.27.58.1/24' or '10.10.0.1/16'
    @type address: str
    @param base: IPv6 reserved base. Default: 'FD32:00F5:0000::'
    @type base: str
    """
    if address.find('/') > -1:
        address, prefix = address.split('/', 1)
        prefix = int(prefix or 0)
    else:
        prefix = 32
    ip_4 = IP(address)
    net_4 = ip_4.make_net(prefix)
    
    #print ip_4.ip
    #print net_4.ip
    
    ip_6 = IP(BASE_IPV6)
    ip_6.ip += (net_4.ip >> (32 - prefix)) << 64
    ip_6.ip += ip_4.ip - net_4.ip
    ip_6._prefixlen = 64
    return ip_6
