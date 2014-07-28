import AbstractConnection
import sys
import socket
import string
import Mumble_pb2
import time
import ssl
import platform
import struct
import thread


class MumbleConnection(AbstractConnection.AbstractConnection):
    # lookup table required for protobuf message type -> message type ID
    _messageLookupMessage = {
        Mumble_pb2.Version: 0,
        Mumble_pb2.UDPTunnel: 1,
        Mumble_pb2.Authenticate: 2,
        Mumble_pb2.Ping: 3,
        Mumble_pb2.Reject: 4,
        Mumble_pb2.ServerSync: 5,
        Mumble_pb2.ChannelRemove: 6,
        Mumble_pb2.ChannelState: 7,
        Mumble_pb2.UserRemove: 8,
        Mumble_pb2.UserState: 9,
        Mumble_pb2.BanList: 10,
        Mumble_pb2.TextMessage: 11,
        Mumble_pb2.PermissionDenied: 12,
        Mumble_pb2.ACL: 13,
        Mumble_pb2.QueryUsers: 14,
        Mumble_pb2.CryptSetup: 15,
        Mumble_pb2.ContextActionAdd: 16,
        Mumble_pb2.ContextAction: 17,
        Mumble_pb2.UserList: 18,
        Mumble_pb2.VoiceTarget: 19,
        Mumble_pb2.PermissionQuery: 20,
        Mumble_pb2.CodecVersion: 21}

    # call the superconstructor and set global configuration variables.
    def __init__(self, hostname, port, nickname, channel, password, name,
                 loglevel):
        super(MumbleConnection, self).__init__(name, loglevel)
        self._hostname = hostname
        self._port = port
        self._nickname = nickname
        self._channel = channel
        self._password = password

        # build the message lookup number table.
        # TODO use a dict comprehension...
        # and define those things outside the class...
        # and rename them....
        # what was I thinking back then?
        self._messageLookupNumber = {}
        for i in self._messageLookupMessage.keys():
            self._messageLookupNumber[self._messageLookupMessage[i]] = i

        # channel id lookup table
        self._channelIds = {}
        # user id lookup table (and reverse)
        self._users = {}
        self._userIds = {}
        # current session and channel id
        self._session = None

        self._socket = None
        # contains all received, but uninterpreted data.
        self._readBuffer = ""

    def _openConnection(self):
        """
        open the (SSL) socket and return True.
        # TODO: support server certificate validation, provide client cert
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self._hostname, self._port))
            self._log("trying python default ssl socket", 3)
            self._socket = ssl.wrap_socket(s)
            return True
        except ssl.SSLError:
            try:
                s.close()
            except:
                pass

        try:
            self._log("python default ssl connection failed, trying TLSv1", 2)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self._hostname, self._port))
            self._socket = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_TLSv1)
            return True
        except ssl.SSLError:
            try:
                s.close()
            except:
                pass
            raise Exception("Error setting up the SSL/TLS socket to murmur.")

    def _initConnection(self):
        # send version package.
        pbMess = Mumble_pb2.Version()
        pbMess.release = "1.2.4"
        pbMess.version = 66048
        pbMess.os = platform.system()
        pbMess.os_version = "mumblebot lol"
        if not self._sendMessage(pbMess):
            raise Exception("couldn't send version package", 0)
        # send auth package.
        pbMess = Mumble_pb2.Authenticate()
        pbMess.username = self._nickname
        if self._password is not None:
            pbMess.password = self._password
        if not self._sendMessage(pbMess):
            raise Exception("couldn't send auth package", 0)
        # great success.
        return True

    def _postConnect(self):
        """
        start ping loop; connection is _not_ established yet.
        """
        thread.start_new_thread(self._pingLoop, ())
        return True

    def _closeConnection(self):
        self._channelId = None
        self._session = None
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        return True

    def _listen(self):
        """
        read and interpret data from socket.
        """
        header = self._socket.recv(6)
        if len(header) == 6:
            (mid, size) = struct.unpack(">HI", header)
        else:
            raise Exception("expected 6 bytes, but got " + str(len(header)))

        data = self._socket.recv(size)

        # look up the message type and invoke the message type's constructor.
        try:
            messagetype = self._messageLookupNumber[mid]
            pbMess = messagetype()
        except:
            self._log("unknown package id: " + str(mid), 1)
            return True

        # parse the message.
        if messagetype != Mumble_pb2.UDPTunnel:
            try:
                pbMess.ParseFromString(data)
            except:
                self._log("message could not be parsed corerctly, type: " +
                          messagetype.__name__, 1)
                return True

        # handle the message.
        if messagetype == Mumble_pb2.ServerSync:
            self._log("server sync package received. session="
                      + str(pbMess.session), 1)
            self._session = pbMess.session
            self._joinChannel(self._channel)
        elif messagetype == Mumble_pb2.ChannelState:
            self._log("channel state package received", 2)
            if(pbMess.name):
                self._log("channel " + pbMess.name + " has id " +
                          str(pbMess.channel_id), 2)
                self._channelIds[pbMess.name] = pbMess.channel_id
        elif messagetype == Mumble_pb2.TextMessage:
            try:
                sender = self._users[pbMess.actor]
            except:
                sender = "unknown"
                self._log("unknown text message sender id: " +
                          str(pbMess.actor), 3)
            self._log("text message received, sender: " + sender, 2)
            self._invokeTextCallback(sender, pbMess.message)
        elif messagetype == Mumble_pb2.UserState:
            self._log("user state package received.", 2)
            if(pbMess.name and pbMess.session):
                self._users[pbMess.session] = pbMess.name
                self._userIds[pbMess.name] = pbMess.session
                self._log("user " + pbMess.name + " has id " +
                          str(pbMess.session), 2)

            if ((pbMess.channel_id is not None and
                 pbMess.session == self._session)):

                self._channelId = pbMess.channel_id
                self._log("I was dragged into another channel. Channel id:" +
                          str(pbMess.channel_id), 2)

        elif messagetype == Mumble_pb2.UDPTunnel:
            self._log("won't analyze your voice packages, sorry", 4)
        elif messagetype == Mumble_pb2.Ping:
            self._log("ping answer received", 3)
        else:
            self._log("unhandeled package received: " + messagetype.__name__ +
                      ", " + str(size) + " bytes", 2)
        return True

    def _sendMessageUnsafe(self, message):
        stringMessage = message.SerializeToString()
        length = len(stringMessage)
        header = struct.pack(">HI", self._messageLookupMessage[type(message)],
                             length)
        packedMessage = header + stringMessage
        while len(packedMessage) > 0:
            sent = self._socket.send(packedMessage)
            if sent < 0:
                raise Exception("could not send message")
            packedMessage = packedMessage[sent:]
        return True

    def _sendTextMessageUnsafe(self, message):
        """
        send message as a TextMessage.
        """
        pbMess = Mumble_pb2.TextMessage()
        pbMess.session.append(self._session)
        pbMess.channel_id.append(self._channelId)
        pbMess.message = message
        self._log("sending text message: " + message, 2)
        return self._sendMessage(pbMess)

    def _pingLoop(self):
        while self._connected:
            pbMess = Mumble_pb2.Ping()
            if not self._sendMessage(pbMess):
                self._log("failed to send ping message", 1)
            time.sleep(10)

    def _joinChannel(self, channel):
        """
        join a channel by name
        """
        if not self._session:
            self._log("can't join channel: no valid session id", 1)
            return False

        try:
            cid = self._channelIds[channel]
        except:
            self._log("can't join channel " + channel + ": unknown id.", 1)
            return False
        self._log("sending package to join channel " + channel +
                  " (id " + str(cid) + ")", 2)

        pbMess = Mumble_pb2.UserState()
        pbMess.session = self._session
        pbMess.channel_id = cid
        if not self._sendMessage(pbMess):
            self._log("failed to send join package", 1)
            return False

        self._channelId = cid
        self._connectionEstablished()

    def setComment(self, message=""):
        """
        set user comment
        """
        if not self._session:
            self._log("can't set user comment: no valid session id", 1)
            return False

        if len(message) > 128:
            # longer comments would require handling RequestBlob messages
            self._log("can't set user comment: too long (>128 bytes)", 1)
            return False

        pbMess = Mumble_pb2.UserState()
        pbMess.session = self._session
        pbMess.comment = message
        pbMess.channel_id = self._channelId
        if not self._sendMessage(pbMess):
            self._log("failed to send comment package", 1)
            return False

        return True
