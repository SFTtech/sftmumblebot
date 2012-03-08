#!/usr/bin/python3

import socket
import ssl
import platform
import struct
import threading

import Mumble_pb2

class MumbleConnection:
    _socket = None
    _hostname = None
    _port = None
    _password = None
    _nickname = None

    _messageLookupMessage = {
            Mumble_pb2.Version:0,
            Mumble_pb2.UDPTunnel:1,
            Mumble_pb2.Authenticate:2,
            Mumble_pb2.Ping:3,
            Mumble_pb2.Reject:4,
            Mumble_pb2.ServerSync:5,
            Mumble_pb2.ChannelRemove:6,
            Mumble_pb2.ChannelState:7,
            Mumble_pb2.UserRemove:8,
            Mumble_pb2.UserState:9,
            Mumble_pb2.BanList:10,
            Mumble_pb2.TextMessage:11,
            Mumble_pb2.PermissionDenied:12,
            Mumble_pb2.ACL:13,
            Mumble_pb2.QueryUsers:14,
            Mumble_pb2.CryptSetup:15,
            Mumble_pb2.ContextActionAdd:16,
            Mumble_pb2.ContextAction:17,
            Mumble_pb2.UserList:18,
            Mumble_pb2.VoiceTarget:19,
            Mumble_pb2.PermissionQuery:20,
            Mumble_pb2.CodecVersion:21}
    
    _messageLookupNumber = {}

    _sendingLock = None
    _receivingLock = None

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

        # build the message lookup number table
        for i in self._messageLookupMessage.keys():
            self._messageLookupNumber[self._messageLookupMessage[i]] = i

        # mutexes for sending and receiving
        self._sendingLock = threading.Lock();
        self._receivingLock = threading.Lock();

    def connectToServer(self):
        pbMess = Mumble_pb2.Version()
        pbMess.release = "1.2.0"
        pbMess.version = 66048
        pbMess.os = platform.system()
        pbMess.os_version = "mumblebot lol"
        if not self.packageAndSend(pbMess):
            print "couldn't send version packet, wtf?!"
            return false

        pbMess = Mumble_pb2.Authenticate()
        pbMess.username = self._nickname
        if self._password != None:
            pbMess.password = self._password

        if not self.packageAndSend(pbMess):
            print "couldn't send auth packet, wtf?!"
            return false
  
    def packageAndSend(self, message):
        stringMessage = message.SerializeToString()
        length = len(stringMessage)
        packedMessage = struct.pack(">HI", self._messageLookupMessage[type(message)], length) + stringMessage
        self._sendingLock.acquire()
        success = False
        try:
            # synchronized gschichtn
            while len(packedMessage) > 0:
                sent = self._socket.send(packedMessage)
                if sent < 0:
                    break
                packedMessage = packedMessage[sent:]
            success = True
        finally:
            self._sendingLock.release()
            return success
