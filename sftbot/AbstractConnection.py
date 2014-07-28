import sys
import socket
import string
import thread
import threading
import traceback
import util


class AbstractConnection(object):
    """
    abstract connection object that specifies the connection's interface.

    MumbleConnection, IRCConnection and others inherit from this.
    """

    def __init__(self, name, loglevel):
        """
        MUST NOT build an actual connection, just store config values.

        MAY be overloaded.
        Overloads MUST call this function as superconstructor.
        """
        # mutex for sending raw data
        self._sendingLock = threading.Lock()
        self._loglevel = loglevel
        # are we currently connected, and have all initial packages been sent?
        self._connected = False
        # is the connection currently fully established?
        # (does it allow sending messages?)
        self._established = False
        # bot name (mainly for logging)
        self._name = name

        # the following lists are callback functions that will be invoked...
        # on text message receipt
        self._textCallback = []
        # on connection establishment
        self._connectionEstablishedCallback = []
        # on connection loss
        self._connectionLostCallback = []
        # on connection attempt failure
        self._connectionFailedCallback = []

    def _openConnection(self):
        """
        SHOULD open sockets/files etc.

        returns True IFF the connection was successfully opened.

        on error, returns False, or raises an exception containing a
        description.

        MUST be overloaded.
        """
        raise NotImplementedError("_openConnection() not implemented in " +
                                  "abstract class AbstractConnection")

    def _initConnection(self):
        """
        SHOULD send initial packages, launch PING threads, etc.

        returns True on success.

        on error, returns False, or raises an exception containing a
        description.

        MUST be overloaded, but may be just 'return true'.
        """
        raise NotImplementedError("_initConnection() not implemented in " +
                                  " abstract class AbstractConnection")

    def _postConnect(self):
        """
        MAY call _connectionEstablished(), but for some heavier protocols
        like Mumble, it may be too early for that.

        called before entering the listening loop.

        returning False or raising an error will immediately close the
        connection, causing it to _not_ enter the listening loop.

        MAY be overloaded.
        """
        self._connectionEstablished()
        return True

    def _closeConnection(self):
        """
        SHOULD close the socket/file.

        returns True on success, and if the connection was open beforehand.

        MUST be overloaded.
        """
        raise NotImplementedError("_closeConnection() not implemented in " +
                                  "abstract class AbstractConnection")

    def _listen(self):
        """
        Called from the main listening loop.

        SHOULD read data from socket/file, and send responses.

        return False or raise an error if listening fails.
        the loop will be cleanly terminated in that case.

        MUST be overloaded.
        """
        raise NotImplementedError("_listen() not implemented in " +
                                  "abstract class AbstractConnection")

    def _sendMessageUnsafe(self, message):
        """
        SHOULD send the message via the connection's socket/file.

        return False or raise an error if the sending fails.

        MUST be overloaded.
        """
        raise NotImplementedError("_sendMessageUnsafe() not implemented in " +
                                  "abstract class AbstractConnection")

    def _sendTextMessageUnsafe(self, message):
        """
        Sends a text message.

        return False or raise an error if the sending has failed.

        SHOULD add the neccesary 'text message' headers to the message,
        and call _sendMessage().

        MUST be overloaded.
        """
        raise NotImplementedError("sendTextMessage() not implemented in " +
                                  "abstract class AbstractConnection")

    # the following methods SHOULD NOT be overloaded.

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

    def start(self):
        """
        call this to start the connection, as a thread.
        """
        thread.start_new_thread(self.run, ())

    def stop(self):
        """
        call this to terminate the connection.
        """
        self._connected = False
        self._established = False

    def _connectionEstablished(self):
        """
        MUST be called manually, as soon as the connection is ready to
        transmit text messages.
        """
        if not self._connected:
            raise Exception("connection can't be established, since it's " +
                            "not even connected")
        self._established = True
        self._invokeConnectionEstablishedCallback()

    def run(self):
        """
        opens and initializes the connection, contains the listening loop,
        and closes the connection.
        """
        try:
            if not self._openConnection():
                raise Exception("unknown error")
        except:
            self._log("connection could not be opened:\n" +
                      str(sys.exc_info()[0]), 0)
            self._log(traceback.format_exc(), 1)
            self._invokeConnectionFailedCallback()
            return
        else:
            self._log("connection successfully opened", 2)

        try:
            if not self._initConnection():
                raise Exception("unknown error")
        except:
            self._logException("initial packages could not be sent", 1)
            try:
                self._closeConnection()
            except:
                pass
            self._invokeConnectionFailedCallback()
            return
        else:
            self._log("initial packages successfully sent", 2)

        # we can now consider ourselves connected.
        # please note that the connection does not count as 'established' yet,
        # as authorization may still be required.
        # call _connectionEstablished() yourself.
        self._connected = True

        try:
            # ... for example from _postConnect()!
            if not self._postConnect():
                raise Exception("postConnect error")

            # you may even call it from inside _listen() once that auth
            # confirm arrives.
            while self._connected:
                if not self._listen():
                    raise Exception("listening error")

        except:
            self._logException("connection terminated with error", 0)
        else:
            self._log("connection terminated without error", 1)

        self._established = False
        self._connected = False

        # try to close the file/socket, in case it's still open.
        try:
            if not self._closeConnection():
                raise Exception("unknown error")
        except:
            self._logException("could not close socket", 1)
        else:
            self._log("socket successfully closed", 2)

        # invoke the connectionLost callback functions.
        self._invokeConnectionLostCallback()

    def _sendMessage(self, message):
        """
        sends a message, taking care of thread-safety and error handling.
        calls _sendMessageUnsafe to do the actual job; overload that.
        """
        with self._sendingLock:
            try:
                # synchronized gschichten.
                if not self._sendMessageUnsafe(message):
                    return False
            except:
                self._logException("could not send message", 1)
                self._connected = False
                return False
            return True

    def sendTextMessage(self, message):
        """
        sends a text message, taking care of thread-safety and error
        handling.
        calls _sendTextMessageUnsafe to do the actual job; overload
        that. From _sendTextMessageUnsafe, _sendMessage MUST be
        called.
        """
        try:
            if not self._established:
                raise Exception("connection not established")
            if not self._sendTextMessageUnsafe(message):
                raise Exception("unknown error")
        except:
            self._logException("could not send text message", 1)

    def _log(self, message, level):
        if(self._loglevel >= level):
            for line in message.split('\n'):
                output = "(" + str(level) + ") " + self._name + ":"
                output = output.ljust(15)
                output = output + util.try_encode(line, 'utf-8')
                print(output)

    def _logException(self, message, level):
        self._log(message + ": " + str(sys.exc_info()[0]), level)
        self._log(traceback.format_exc(), level + 1)
