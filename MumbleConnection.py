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

	# lookup table required for getting message type Ids from message types.
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
	# lookup table required for getting message types from message type Ids.
	# will be auto-generated from messageLookupMessage during __init__.
	_messageLookupNumber = {}

	# lookup table required for translating channel names to channel Ids.
	# will be auto-generated from channelState messages.
	_channelIds = {}

	# lookup tables required for translating user names to session Ids and vice-versa.
	# every user has a own session and session id so we're using this instead of the user id
	# see line 172 for more
	# will be auto-generated from userState messages.
	_users = {}
	_userIds = {}

	# the bot's session and channel id.
	_session = None

	# call the superconstructor and set global configuration variables.
	def __init__(self, hostname, port, nickname, channel, password, tokens, name, loglevel):
		super(MumbleConnection,self).__init__(name, loglevel)
		self._hostname = hostname
		self._port = port
		self._nickname = nickname
		self._channel = channel
		self._password = password
		self._tokens = tokens
		# build the message lookup number table.
		for i in self._messageLookupMessage.keys():
			self._messageLookupNumber[self._messageLookupMessage[i]] = i

		# the (SSL) socket that will be used for communication with the mumble server.
		self._socket = None
		# the read buffer, which contains all currently read, but uninterpreted data.
		self._readBuffer = ""

	# open the socket and return true. don't catch exceptions, since the run() wrapper will do that.
	def _openConnection(self):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((self._hostname, self._port))
		try:
			self._log("trying python default ssl socket", 3)
			self._socket = ssl.wrap_socket(s)
		except ssl.SSLError:
			try:
				s.close()
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s.connect((self._hostname, self._port))
				self._log("python default ssl connection failed, trying TLSv1", 3)
				self._socket = ssl.wrap_socket(s, ssl_version = ssl.PROTOCOL_TLSv1)
			except ssl.SSLError:
				raise Exception("Error setting up the SSL/TLS socket to murmur.")
		return True

	# send initial packages (version and auth).
	def _initConnection(self):
		# send version package.
		pbMess = Mumble_pb2.Version()
		pbMess.release = "1.2.0"
		pbMess.version = 66048
		pbMess.os = platform.system()
		pbMess.os_version = "mumblebot lol"
		if not self._sendMessage(pbMess):
			raise Exception("couldn't send version package", 0)
		# send auth package.
		pbMess = Mumble_pb2.Authenticate()
		pbMess.username = self._nickname
		if self._password != None:
			pbMess.password = self._password
		for token in self._tokens:
			pbMess.tokens.append(token)
		if not self._sendMessage(pbMess):
			raise Exception("couldn't send auth package", 0)
		# great success.
		return True

	# post-connect, start the ping loop. we can not consider ourselves connected yet.
	def _postConnect(self):
		thread.start_new_thread(self._pingLoop, ())
		return True

	# close the socket.
	def _closeConnection(self):
		self._channelId = None
		self._session = None
		self._socket.shutdown(socket.SHUT_RDWR)
		self._socket.close()
		return True


	# read and interpret data from socket in this method.
	def _listen(self):
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
				self._log("message could not be parsed corerctly, message type: "+messagetype.__name__, 1)
				return True

		# handle the message.
		
		if messagetype == Mumble_pb2.ServerSync:
			self._log("server sync package received. session=" + str(pbMess.session), 1)
			self._session = pbMess.session
			self._joinChannel(self._channel)
		
		elif messagetype == Mumble_pb2.ChannelState:
			self._log("channel state package received", 2)
			if(pbMess.name):
				self._log("channel " + pbMess.name + " has id " + str(pbMess.channel_id), 2)
				self._channelIds[pbMess.name] = pbMess.channel_id
		
		elif messagetype == Mumble_pb2.TextMessage:
			try:
				sender = self._users[pbMess.actor]
			except:
				sender = "unknown"
				self._log("unknown text message sender id: " + str(pbMess.actor), 3)
			self._log("text message received, sender: " + sender, 2)
			self._invokeTextCallback(sender, pbMess.message)
		
		elif messagetype == Mumble_pb2.UserState:
			self._log("user state package received.", 2)
			if(pbMess.name and pbMess.session):
				self._users[pbMess.session] = pbMess.name
				self._userIds[pbMess.name] = pbMess.session
				self._log("user " + pbMess.name + " has id " + str(pbMess.session), 2)
			if(pbMess.channel_id != None and pbMess.session == self._session):
				self._channelId = pbMess.channel_id
				self._log("I was dragged into another channel. Channle id:" + str(pbMess.channel_id), 2)

		elif messagetype == Mumble_pb2.UserRemove and pbMess.actor:  # kick UserRemove
			self._log("Got a \"kick\" UserRemove Message", 2)
			return True
	
		# actually there are 2 types of UserRemove packages:
		# 1. those sent when a User disconnects
		# 2. those sent when a User is kicked
		# 2 distinguishes from 1 by the fact that it has more attributes ( i.e. an actor attribut for the kicker)
		# when a user is kicked firstly 2 is sent AND then an instance of 1 too.
		# So just handling generic User remove Packages would lead to an Error because the User would be 
		# removed 2 times from the local dict of mumblebot.
		# This is why packages of Type 2 are "ignored" above: 
		# That way in a kick case the first "kick" UserRemove package 
		# is ignored and the user gets removed from the second ordinary "disconnect" UserRemove.

		elif messagetype == Mumble_pb2.UserRemove and not pbMess.actor:  # disconnect UserRemove
			self._log("Got \"disconnect\" UserRemove Message", 2)
			if self._users[pbMess.session] in self._userIds:
				del self._userIds[self._users[pbMess.session]]
			if pbMess.session in self._users:
				del self._users[pbMess.session] 

		elif messagetype == Mumble_pb2.UDPTunnel:
			self._log("won't analyze your voice packages, sorry", 4)
		
		elif messagetype == Mumble_pb2.Ping:
			self._log("ping answer received", 3)
		
		else:
			self._log("unhandeled package received: " + messagetype.__name__ + ", " + str(size) + " bytes", 2)
		return True

	# send the given line via the socket. don't catch any exceptions.
	def _sendMessageUnsafe(self, message):
		stringMessage = message.SerializeToString()
		length = len(stringMessage)
		packedMessage = struct.pack(">HI", self._messageLookupMessage[type(message)], length) + stringMessage
		while len(packedMessage) > 0:
			sent = self._socket.send(packedMessage)
			if sent < 0:
				raise Exception("could not send message")
			packedMessage = packedMessage[sent:]
		return True

	# pass the given line to _sendMessage, encoded as a PRIVMSG to #self._channel.
	def _sendTextMessageUnsafe(self, message):
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
		if not self._session:
			self._log("can't join channel since we don't have a valid session id", 1)
			return False

		try:
			cid = self._channelIds[channel]
		except:
			self._log("the channel id for "+channel+" could not be resolved. can't join channel.", 1)
			return False
		self._log("sending package to join channel " + channel + " (id " + str(cid) + ")", 2)

		pbMess = Mumble_pb2.UserState()
		pbMess.session = self._session
		pbMess.channel_id = cid
		if not self._sendMessage(pbMess):
			self._log("failed to send join package", 1)
			return False

		self._channelId = cid
		self._connectionEstablished()
