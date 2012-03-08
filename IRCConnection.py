import sys
import socket
import string
import thread

class IRCConnection:
    _readbuffer = ""
    _socket = None

    #the mutex used when sending packets.
    _sendingLock = None

    def __init__(self, hostname, port, nickname, channel):
        self._socket=socket.socket()
        self._socket.connect((hostname, port))
        self._sendingLock = threading.Lock();
        sendRawString("NICK %s" % nickname)
        sendRawString("USER %s %s bla :%s\n" % (nickname, hostname, nickname))
        thread.start_new_thread(self.listeningLoop, ())

    def listeningLoop(self):
        while True:
            readbuffer=readbuffer + s.recv(1024)
            temp=string.split(readbuffer, "\n")
            readbuffer=temp.pop()

            for line in temp:
                print("rx: "+line)
                line=string.rstrip(line)
                line=string.split(line)
                print("rx+ "+line)

            if(line[0]=="PING"):
                sendRawString("PONG %s" % line[1])

    def sendRawString(self, message):
        self._sendingLock.acquire()
        try:
            # synchronized gschichtn
            print("tx: "+message)
            self._socket.send(message + "\n")
        finally:
            self._sendingLock.release()
            return success

    #a list of all callback functions that will be invoked when a text message is received.
    _textCallback = []

    def messageReceived(self, text):
        for f in self._textCallback:
            f(text)

    def registerTextCallback(self, function):
        self._textCallback.append(function)
