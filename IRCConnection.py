import sys
import socket
import string
import thread
import threading

class IRCConnection:
    _readbuffer = ""
    _socket = None
    _channel = None

    #the mutex used when sending packets.
    _sendingLock = None

    _loglevel = 0

    def __init__(self, hostname, port, nickname, channel, loglevel):
        self._socket=socket.socket()
        self._socket.connect((hostname, port))
        self._channel = channel
        self._sendingLock = threading.Lock()
        self._loglevel = loglevel
        self.sendRawString("NICK %s" % nickname)
        self.sendRawString("USER %s %s bla :%s" % (nickname, hostname, nickname))
        self.sendRawString("JOIN #%s" % channel)
        thread.start_new_thread(self.listeningLoop, ())

    def log(self, message, level):
        if(self._loglevel >= level):
            print(message)

    def listeningLoop(self):
        while True:
            self._readbuffer=self._readbuffer + self._socket.recv(1024)
            temp=string.split(self._readbuffer, "\n")
            self._readbuffer=temp.pop()

            for line in temp:
                self.log("rx: "+line, 3)
                line=string.rstrip(line)
                line=line.split(' ', 3)
                self.log("rx+:"+str(line), 4)

            if(len(line) >= 2):
                if(line[0]=="PING"):
                    self.sendRawString("PONG %s" % line[1])

            if(len(line) >= 4):
                if(line[1]=="PRIVMSG"):
                    self.messageReceived(line[0].split('!~')[0].strip(': '), line[3].strip(': '))

    def sendRawString(self, message):
        self._sendingLock.acquire()
        try:
            # synchronized gschichtn
            self.log("tx: "+message, 2)
            self._socket.send(message.encode('ascii') + "\n")
        finally:
            self._sendingLock.release()
   
    def sendTextMessage(self, message):
        self.sendRawString("PRIVMSG #" + self._channel + " :" + message)

    #a list of all callback functions that will be invoked when a text message is received.
    _textCallback = []

    def messageReceived(self, sender, text):
        text = text.decode('ascii')
        for f in self._textCallback:
            f(sender, text)

    def registerTextCallback(self, function):
        self._textCallback.append(function)
