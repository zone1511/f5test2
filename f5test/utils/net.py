from netaddr import IPNetwork
import socket

BASE_IPV6 = 'FD32:00F5:0000::/64'

def resolv(hostname):
    """Resolves a hostname into an IP address."""
    try:
        _, _, ip_list = socket.gethostbyaddr(hostname)
    except socket.herror: # [Errno 1] Unknown host
        return hostname
    return ip_list[0]

def get_local_ip(peer):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((peer.split(':', 1)[0], 0))
    ip = s.getsockname()[0]
    s.close()
    return ip

def ip4to6(ipv4, base=BASE_IPV6):
    """
    Convert an IPv4 to IPv6 by splitting the network part of the ip and shifting
    it to the Global ID and Subnet ID zone.
    
    @param address: IPv4 address (e.g. '172.27.58.1/24' or '10.10.0.1/16'
    @type address: str
    @param base: IPv6 reserved base. Default: 'FD32:00F5:0000::'
    @type base: str
    """
    ipv4 = IPNetwork(ipv4)
    ipv6 = IPNetwork(BASE_IPV6)
    ipv6.value += (ipv4.value >> (32 - ipv4.prefixlen)) << 64
    ipv6.value += ipv4.value - ipv4.network.value
    return ipv6
