import sys
import socket
import string
import thread
import threading
import traceback

class IRCConnection:
    # some global configuration variabels set by the constructor
    _socket = None
    _channel = None
    _hostname = None
    _nickname = None
    _port = None
    _loglevel = 0
    _encoding = None

    # the mutex used when sending lines
    _sendingLock = None

    # the buffer used for reading from the socket 
    _readbuffer = ""

    # this variable stores if we're currently connected
    _connected = False

    #a list of all callback functions that will be invoked when a text message is received.
    _textCallback = []
    #a list of all callback functions that will be invoked when the connection is established.
    _connectionEstablishedCallback = []
    #a list of all callback functions that will be invoked when the connection is lost.
    _connectionLostCallback = []
    #a list of all callback functions that will be invoked when a connection attempt fails.
    _connectionFailedCallback = []

    def registerTextCallback(self, function):
        self._textCallback.append(function)

    def registerConnectionEstablishedCallback(self, function):
        self._connectionEstablishedCallback.append(function)

    def registerConnectionLostCallback(self, function):
        self._connectionLostCallback.append(function)

    def registerConnectionFailedCallback(self, function):
        self._connectionFailedCallback.append(function)

    def __init__(self, hostname, port, nickname, channel, encoding, loglevel):
        self._port = port
        self._hostname = hostname
        self._channel = channel
        self._sendingLock = threading.Lock()
        self._loglevel = loglevel
        self._connected = False
        self._encoding = encoding
        self._nickname = nickname

    def start(self):
        thread.start_new_thread(self.run, ())

    def stop(self):
        self._connected = False

    def run(self):
        try:
            self._socket = socket.socket()
            self._socket.connect((self._hostname, self._port))
        except:
            self.log("couldn't establish connection to host " + self._hostname + " port " + str(self._port), 0)
            # invoke the connectionFailed callback functions
            for f in self._connectionFailedCallback:
                f()
            return

        try:
            self._sendRawString("NICK %s" % self._nickname)
            self._sendRawString("USER %s %s bla :%s" % (self._nickname, self._hostname, self._nickname))
            self._sendRawString("JOIN #%s" % self._channel)
        except:
            self.log("couldn't send NICK/USR/JOIN messages to socket", 0)
            # invoke the connectionFailed callback functions
            for f in self._connectionFailedCallback:
                f()
            return

        # we can now consider ourselves connected
        self._connected = True

        # invoke the connectionEstablished callback functions
        for f in self._connectionEstablishedCallback:
            f()

        try:
            self.listeningLoop()
        except:
            self.log("exception in ircConnection listeningLoop:\n"+traceback.format_exc(), 0)
        self._connected = False
        
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
            self._socket.close()
        except:
            self.log("socket could not be shut down and closed:\n"+traceback.format_exc(), 1)
        
        # invoke the connectionLost callback functions
        for f in self._connectionLostCallback:
            f()

    def log(self, message, level):
        if(self._loglevel >= level):
            print(message)

    def listeningLoop(self):
        while self._connected:
            # read a chunk of data from socket, into the read buffer
            self._readbuffer += self._socket.recv(1024)

            # split the data in lines, store these in temp. leave the beginning of the last line in the read buffer
            temp=string.split(self._readbuffer, "\n")
            self._readbuffer=temp.pop()

            # iterate over all received lines
            for line in temp:
                # split the line at space characters
                # it would be more clean to split it only until the first colon is received, but we're too lazy for that
                self.log("rx: "+line, 3)
                line=string.rstrip(line)
                line=line.split(' ', 3)
                self.log("rx+:"+str(line), 4)

                # check if the message is a PING message. if yes, respond with PONG to stay alive
                if(len(line) >= 2):
                    if(line[0]=="PING"):
                        self._sendRawString("PONG %s" % line[1])

                # check if the message is a PRIVMSG message. if yes, parse it and call the appropriate callback methods
                if(len(line) >= 4):
                    if(line[1]=="PRIVMSG"):
                        self._messageReceived(line[0].split('!~')[0].lstrip(': '), line[3].lstrip(': '))

    def _sendRawString(self, message):
        self._sendingLock.acquire()
        try:
            # synchronized gschichtn
            self.log("tx: "+message, 2)
            self._socket.send(message.encode(self._encoding, errors='ignore') + "\n")
        finally:
            self._sendingLock.release()
   
    def sendTextMessage(self, message):
        if not self._connected:
            self.log("warning: tried to send text message, but not connected", 1)

        # send the message
        self._sendRawString("PRIVMSG #" + self._channel + " :" + message)

    #a list of all callback functions that will be invoked when a text message is received.
    _textCallback = []

    def _messageReceived(self, sender, text):
        text = text.decode(self._encoding, errors='ignore')
        for f in self._textCallback:
            f(sender, text)
