import socket
import ssl
import platform
import struct
import thread
import threading
import binascii
import time
import traceback

import Mumble_pb2

class MumbleConnection:
    # some global configuration variables set by the constructor
    _socket = None
    _hostname = None
    _port = None
    _password = None
    _nickname = None    
    _channel = None
    _loglevel = 0

    # lookup table required for getting message type Ids from message types
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
    # lookup table required for getting message types from message type Ids
    # will be auto-generated from messageLookupMessage during __init__
    _messageLookupNumber = {}

    # lookup table required for translating channel names to channel Ids
    # will be auto-generated from channelState messages
    _channelIds = {}

    # lookup tables required for translating user names to user Ids and vice-versa
    # will be auto-generated from userState messages
    _users = {}
    _userIds = {}

    # the bot's session and channel id
    _session = None
    _channelId = None

    #the mutex used when sending packets.
    _sendingLock = None

    #a list of all callback functions that will be invoked when a text message is received.
    _textCallback = []
    #a list of all callback functions that will be invoked when the connection is established.
    _connectionEstablishedCallback = []
    #a list of all callback functions that will be invoked when the connection is lost.
    _connectionLostCallback = []
    #a list of all callback functions that will be invoked when a conneciton attempt fails.
    _connectionFailedCallback = []

    #stores if we're currently connected to the server.
    _connected = False

    def log(self, message, level):
        if(self._loglevel >= level):
            print(message)

    def __init__(self, hostname, port, password, nickname, channel, loglevel):
        # normally we would check the parameters for plausibility, but we're too lazy. we trust them to be well-formed
        self._hostname = hostname
        self._port = port
        self._password = password
        self._nickname = nickname
        self._channel = channel
        self._loglevel = loglevel
        self._connected = False

        # build the message lookup number table
        for i in self._messageLookupMessage.keys():
            self._messageLookupNumber[self._messageLookupMessage[i]] = i

        # init mutex for sending
        self._sendingLock = threading.Lock()

    def start(self):
        thread.start_new_thread(self.run, ())

    def stop(self):
        self._connected = False

    def run(self):
        # if we're already connected, abort
        if(self._connected):
           return
        
        # now, we gschichtl a socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self._hostname, self._port))
            # ssl voodoo
            self._socket = ssl.wrap_socket(s)
        except:
            self.log("couldn't establish ssl connection to host " + self._hostname + " port " + str(self._port), 0)
            # invoke the connectionFailed callback functions
            for f in self._connectionFailedCallback:
                f()
            return

        # send version package
        pbMess = Mumble_pb2.Version()
        pbMess.release = "1.2.0"
        pbMess.version = 66048
        pbMess.os = platform.system()
        pbMess.os_version = "mumblebot lol"
        if not self.packageAndSend(pbMess):
            self.log("couldn't send version packet, wtf?!", 0)
            # invoke the connectionFailed callback functions
            for f in self._connectionFailedCallback:
                f()
            return

        # send auth package
        pbMess = Mumble_pb2.Authenticate()
        pbMess.username = self._nickname
        if self._password != None:
            pbMess.password = self._password

        if not self.packageAndSend(pbMess):
            self.log("couldn't send auth packet, wtf?!", 0)
            # invoke the connectionFailed callback functions
            for f in self._connectionFailedCallback:
                f()
            return

        # we can now consider ourselves connected.
        self._connected = True

        # start the ping loop
        thread.start_new_thread(self.pingLoop, ())

        # invoke the connectionEstablished callback functions
        for f in self._connectionEstablishedCallback:
            f()

        # start the listening loop
        try:
            self.listeningLoop()
        except:
            self.log("exception in mumbleConnection listeningLoop:\n"+traceback.format_exc(), 0)
        self._connected = False
        self._channelId = None
        self._session = None
        try:
            self._socket.shutdown(socket.SHUT_RDWR)            
            self._socket.close()
        except:
            self.log("socket could not be shut down and closed:\n"+traceback.format_exc(), 1)

        # invoke the connectionLost callback functions
        for f in self._connectionLostCallback:
            f()

    def sendTextMessage(self, text):
        if not self._connected:
            self.log("warning: can't send text message since the connection is not established", 1)
            return False

        if not self._session:
            self.log("warning: can't send text message since we don't have a valid session id", 1)
            return False

        if not self._channelId:
            self.log("warning: can't send text message since we've not joined a channel yet", 1)
            return False

        pbMess = Mumble_pb2.TextMessage()
        pbMess.session.append(self._session)
        pbMess.channel_id.append(self._channelId)
        try:
            pbMess.message = text 
        except:
            self.log("warning: can't send text message (protobuf does not accept unicode-coded message):\n" + traceback.format_exc(), 1)
            return False
        self.log("sending text message: "+text, 2)
        if not self.packageAndSend(pbMess):
            self.log("warning: failed to send text message", 1)
            return False
        else:
            return True

    def joinChannel(self, channel):
        if not self._session:
            self.log("warning: can't join channel since we don't have a valid session id", 1)
            return False

        try:
            cid=self._channelIds[channel]
        except:
            self.log("warning: the channel id for "+channel+" could not be looked up", 1)
            return False
        self.log("sending packet to join channel "+channel+" (id "+str(cid)+")", 2)
        pbMess = Mumble_pb2.UserState()
        pbMess.session = self._session 
        pbMess.channel_id = cid
        if not self.packageAndSend(pbMess):
            self.log("warning: failed to send join package", 1)
            return False
        self._channelId = cid
        return True

    def pingLoop(self):
        while self._connected:
            pbMess = Mumble_pb2.Ping()
            if not self.packageAndSend(pbMess):
                self.log("warning: failed to send ping package", 1)    
            time.sleep(10)
  
    def listeningLoop(self):
        while self._connected:
            #receive the 6-byte packet header
            try:
                header = self._socket.recv(6)
            except:
                self.log("error: can't read header of next package from socket", 0)
                break

            #read the 6-byte packet header (split it to message id, message size)
            try:
                (mid, size) = struct.unpack(">HI", header)
            except:
                self.log("error: unpacking of header struct failed. struct content: "+binascii.hexlify(data), 0)
                break

            #receive the packet body
            try:
                data=self._socket.recv(size)
            except:
                self.log("error: failed to read body of package ("+str(size)+" bytes) from socket", 0)
                break

            #look up the message type
            try:
                messagetype=self._messageLookupNumber[mid]
            except:
                messagetype=None
                self.log("warning: unknown package (id "+str(mid)+", "+str(size)+" byte) received", 2)
                continue

            #create message parser
            try:
                message = messagetype()
            except:
                self.log("warning: message parser couldn't be initialized for message type "+messagetype.__name__, 1)
                continue

            #parse the message
            try:
                message.ParseFromString(data)
            except:
                self.log("warning: message could not be parsed correctly, message type: "+messagetype.__name__+", message size: "+str(size)+" byte", 2)
                continue

            #check what kind of gschicht has been received
            if messagetype == Mumble_pb2.ServerSync:
                self.log("server sync package received. setting session to "+str(message.session),1)
                self._session = message.session
                self.joinChannel(self._channel)
            elif messagetype == Mumble_pb2.ChannelState:
                self.log("channelState package received.", 2)
                if(message.name):
                    self.log("\tchannel "+message.name+" has Id "+str(message.channel_id),2)
                    self._channelIds[message.name]=message.channel_id
            elif messagetype == Mumble_pb2.TextMessage:
                try:
                    sender = self._users[message.actor]
                except:
                    sender = "unknown"
                    self.log("\tunknown sender id "+message.actor+" for text message",1)
                self.log("text message received", 2)
                msg = message.message 
                for f in self._textCallback:
                    f(sender, message.message)
            elif messagetype == Mumble_pb2.UserState:
                if(message.name and message.session):
                    self._users[message.session]=message.name
                    self._userIds[message.name]=message.session
                    self.log("userState package received. user "+message.name+" has session "+str(message.session), 2)
                else:
                    self.log("userState package with unknown content received.", 2)
            else:
                self.log(messagetype.__name__+" package ("+str(size)+" byte) received, but not handled", 3)

    def registerTextCallback(self, function):
        self._textCallback.append(function)

    def registerConnectionEstablishedCallback(self, function):
        self._connectionEstablishedCallback.append(function)

    def registerConnectionLostCallback(self, function):
        self._connectionLostCallback.append(function)

    def registerConnectionFailedCallback(self, function):
        self._connectionFailedCallback.append(function)

    def packageAndSend(self, message):
        stringMessage = message.SerializeToString()
        length = len(stringMessage)
        packedMessage = struct.pack(">HI", self._messageLookupMessage[type(message)], length) + stringMessage
        self._sendingLock.acquire()
        success = True
        try:
            # synchronized gschichtn
            while len(packedMessage) > 0:
                sent = self._socket.send(packedMessage)
                if sent < 0:
                    success = False
                    break
                packedMessage = packedMessage[sent:]
        finally:
            self._sendingLock.release()
            return success
