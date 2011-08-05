from socket import socket, gethostbyname_ex, SOCK_DGRAM, AF_INET

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
