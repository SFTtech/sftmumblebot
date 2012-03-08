#!/usr/bin/python3

import socket
import ssl

class MumbleConnection:
    _socket = None
    _hostname = None
    _port = None
    _password = None
    _nickname = None

    def __init__(self, hostname, port, password, nickname):
        # normally we would check the parameters for plausibility, but we're too lazy. we trust them to be well-formed
        self._hostname = hostname
        self._port = port
        self._password = password
        self._nickname = nickname

        # now, we gschichtl a socket.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((hostname, port))
        
        # ssl voodoo
        self._socket = ssl.wrap_socket(s)

if __name__=="__main__":
    mc = MumbleConnection("wue.ensslin.cc", 1337, "Neger", "lolbot")       
