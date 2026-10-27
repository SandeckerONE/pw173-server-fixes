"""Plain-words explanation of why the patch server can't be reached.

Tailscale addresses are 100.64.0.0 - 100.127.255.255. If the server address is one of
those, the PC needs Tailscale running. If it is anything else (the LAN / host-only
address), Tailscale is not involved and the message talks about the VM instead.
"""
import ipaddress
import socket
import urllib.parse

_TAILSCALE = ipaddress.ip_network("100.64.0.0/10")


def is_tailscale_addr(host):
    try:
        return ipaddress.ip_address(host) in _TAILSCALE
    except ValueError:
        return False


def route_source(host):
    """The local address this PC would use to reach host (nothing is sent: a UDP
    'connect' only asks the OS to pick a route). None if there is no route."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((host, 9))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


def hint(server_url):
    """One short sentence of advice for a failed connection to server_url."""
    host = urllib.parse.urlparse(server_url).hostname or ""
    if is_tailscale_addr(host):
        src = route_source(host)
        if src and is_tailscale_addr(src):
            return ("Tailscale looks connected, but the server did not answer. "
                    "The server VM may be off or restarting - try again in a minute.")
        return ("Tailscale does not look connected on this PC. "
                "Open Tailscale, make sure it is signed in and ON, then restart the launcher.")
    return ("The server at %s did not answer. Is the server VM running "
            "(and the host-only network up)?" % host)
