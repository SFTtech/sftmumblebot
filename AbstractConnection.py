import sys
import socket
import string
import thread
import threading
import traceback

class AbstractConnection(object):
	# the constructor should only set global configuration variables according to
	# it's arguments. under no circumstances, it should open a connection. that's the
	# job of the methods invoked by run().
	# you should overload this method, but call the superconstructor in the first line.
	def __init__(self, name, loglevel):
		# the mutex for sending raw data:
		self._sendingLock = threading.Lock()
		#loglevel, the captain obvious among the attributes
		self._loglevel = loglevel
		# this variable stores if we're currently connected, and all neccesary initial packages have been sent:
		self._connected = False
		# this variable stores if the conneciton is fully established, allowing text messages to be sent:
		self._established = False
		# the name of the bot, as it appears in the logs:
		self._name = name

		#a list of all callback functions that will be invoked when a text message is received.
		self._textCallback = []
		#a list of all callback functions that will be invoked when the connection is established:
		self._connectionEstablishedCallback = []
		#a list of all callback functions that will be invoked when the connection is lost:
		self._connectionLostCallback = []
		#a list of all callback functions that will be invoked when a connection attempt fails:
		self._connectionFailedCallback = []

	# do stuff like opening sockets/files.
	# return true if and only if the connection was successfully opened.
	# if an error occured, eighter return false, or raise an exception that contains a detailed description.
	# you need to overload this method.
	def _openConnection(self):
		raise notImplementedError("_openConnection() not implemented in abstract class AbstractConnection")

	# do stuff like sending initial packages or launching a PING thread.
	# return true if and only if the connection was successfully opened.
	# if an error occured, eighter return false, or raise an exception that contains a detailed description.
	# you need to overload this method, even if 'return true' will be it's only content.
	def _initConnection(self):
		raise notImplementedError("_initConnection() not implemented in abstract class AbstractConnection")

	# do stuff like calling _connectionEstablished().
	# return false or raise an error to close the connection immediately before it enters the listening loop.
	# you can, but won't need to, overload this method.
	def _postConnect(self):
		self._connectionEstablished()
		return True

	# do stuff like closing the socket/file.
	# return true if and only if the connection was successfully closed, and if it was still open beforehand.
	# otherwise, eighter return false, or raise an exception that contains a detailed description
	# you need to overload this method.
	def _closeConnection(self):
		raise notImplementedError("_closeConnection() not implemented in abstract class AbstractConnection")

	# contains the main listening loop, which reads data from the socket/file, and sends responses.
	# return false or raise an error if the listening has somehow fatally failed. note that the listening
	# loop will be terminated in that case.
	# you need to overload this method.
	def _listen(self):
		raise notImplementedError("_listen() not implemented in abstract class AbstractConnection")

	# sends the message via the connection's socket/file/etc
	# return false or raise an error if the sending of message has failed.
	# you need to overload this method.
	def _sendMessageUnsafe(self, message):
		raise notImplementedError("_sendMessageUnsafe() not implemented in abstract class AbstractConnection")

	# sends a text message, using _sendMessage().
	# return false or raise an error if the sending of the text message has failed.
	# you need to overload this method.
	def _sendTextMessageUnsafe(self, message):
		raise notImplementedError("sendTextMessage() not implemented in abstract class AbstractConnection")

	def registerTextCallback(self, function):
		self._textCallback.append(function)

	def registerConnectionEstablishedCallback(self, function):
		self._connectionEstablishedCallback.append(function)

	def registerConnectionLostCallback(self, function):
		self._connectionLostCallback.append(function)

	def registerConnectionFailedCallback(self, function):
		self._connectionFailedCallback.append(function)

	def _invokeTextCallback(self, sender, message):
		for f in self._textCallback:
			f(sender, message)

	def _invokeConnectionEstablishedCallback(self):
		for f in self._connectionEstablishedCallback:
			f()

	def _invokeConnectionLostCallback(self):
		for f in self._connectionLostCallback:
			f()

	def _invokeConnectionFailedCallback(self):
		for f in self._connectionFailedCallback:
			f()

	# call this to start the connection, as a thread.
	# you should not overload this method.
	def start(self):
		thread.start_new_thread(self.run, ())

	# call this to terminate the connection
	# you should not overload this method.
	def stop(self):
		self._connected = False
		self._established = False

	# this method needs to be called manually, as soon as the connection is ready to transmit text
	# messages.
	# you should not overload this method.
	def _connectionEstablished(self):
		if not self._connected:
			raise Exception("connection can't be established, since it's not even connected")
		self._established = True
		self._invokeConnectionEstablishedCallback()

	# opens and initializes the connection, contains the listening loop, and closes the connection.
	# you should not overload this method.
	def run(self):
		try:
			if not self._openConnection():
				raise Exception("unknown error")
		except:
			self._log("connection could not be opened:\n" + str(sys.exc_info()[0]), 0)
			self._log(traceback.format_exc(), 1)
			self._invokeConnectionFailedCallback()
			return
		else:
			self._log("connection successfully opened", 2)

		try:
			if not self._initConnection():
				raise Exception("unknown error")
		except:
			self._log("initial packages could not be sent:\n" + str(sys.exc_info()[0]), 0)
			self._log(traceback.format_exc(), 1)
			self._invokeConnectionFailedCallback()
			return
		else:
			self._log("initial packages successfully sent", 2)

		# we can now consider ourselves connected.
		# please note that the connection does not count as established yet,
		# you'll need to call invokeConnectionEstablishedCallback yourself...
		self._connected = True

		try:
			# ... for example in this optional post-connect method.
			if not self._postConnect():
				raise Exception("postConnect error")

			# the main listening loop.
			while self._connected:
				success = self._listen()
				if not success:
					raise Exception("listening error")

		except:
			self._log("connection terminated with an error:\n" + str(sys.exc_info()[0]), 0)
			self._log(traceback.format_exc(), 1)
		else:
			self._log("connection terminated without error", 1)

		self._established = False
		self._connected = False

		# try to close the file/socket, in case it's still open.
		try:
			if not self._closeConnection():
				raise Exception("unknown error")
		except Exception as e:
			self._log("socket could not be closed: " + str(e) + "\n" + str(sys.exc_info()[0]), 1)
			self._log(traceback.format_exc(), 2)
		else:
			self._log("socket successfully closed", 2)

		# invoke the connectionLost callback functions.
		self._invokeConnectionLostCallback()

	# prints a log message to stdout.
	# you should not overload this method.
	def _log(self, message, level):
		if(self._loglevel >= level):
			for line in message.split('\n'):
				try:
					oline = line.encode('utf-8', errors='ignore')
				except:
					oline = repr(line)
				print("(" + str(level) + ") " + self._name + ": " + oline)

	# sends a message, taking care of thread-safety and error handling.
	# calls _sendUnprotectedMessage to do the actual job.
	# you should not overload this method.
	def _sendMessage(self, message):
		with self._sendingLock:
			try:
				# synchronized gschichten.
				if not self._sendMessageUnsafe(message):
					return False
			except:
				self._log("could not send message: " + str(sys.exc_info()[0]), 1)
				self._log(traceback.format_exc(), 2)
				self._connected = False
				return False
			return True

	def sendTextMessage(self, message):
		try:
			if not self._established:
				raise Exception("connection not established")
			if not self._sendTextMessageUnsafe(message):
				raise Exception("unknown error")
		except:
			self._log("could not send text message: " + str(sys.exc_info()[0]), 1)
			self._log(traceback.format_exc(), 2)
