import sys
import thread
import traceback

class Console:
    # some status variables that will be set by the constructor
    _encoding = "utf-8"
    _loglevel = 0

    # this variable stores if we're currently connected
    _connected = False

    # a list of all callback functions that will be invoked when a text message is received.
    _textCallback = []
    # a list of all callback functions that will be invoked when the connection is established.
    _connectionEstablishedCallback = []
    # a list of all callback functions that will be invoked when the connection is lost.
    _connectionLostCallback = []

    def registerTextCallback(self, function):
        self._textCallback.append(function)

    def registerConnectionEstablishedCallback(self, function):
        self._connectionEstablishedCallback.append(function)

    def registerConnectionLostCallback(self, function):
        self._connectionLostCallback.append(function)

    def __init__(self, encoding, loglevel):
        self._encoding=encoding
        self._loglevel=loglevel
        self._connected=False

    def log(self, message, level):
        if(self._loglevel >= level):
            print(message)

    def start(self):
        thread.start_new_thread(self.run, ())

    def stop(self):
        self._connected = False

    def run(self):
        # we can now consider ourselves connected
        self._connected = True

        # invoke the connectionEstablished callback functions
        for f in self._connectionEstablishedCallback:
            f()

        try:
            self.listeningLoop()
        except:
            self.log("exception in console listeningLoop:\n"+traceback.format_exc(), 0)
        self._connected = False

        # invoke the connectionLost callback functions
        for f in self._connectionLostCallback:
            f()

    # will run until keyboard interrupt is receivd.
    def listeningLoop(self):
        while self._connected:
            try:
                line = sys.stdin.readline()
            except KeyboardInterrupt:
                self._messageReceived("console", "Goodbye.")
                self.log("keyboard interrupt", 1)
                break
            except:
                self.log("error reading line from stdin.", 1)

            uline = None
            try:
                uline = line.decode(self._encoding)
            except:
                self.log("decoding the line using the default encoding " + self._encoding + " has failed.", 2)
                try:
                    uline = line.decode('utf-8')
                except:
                    self.log("decoding the line using utf-8 has failed.", 2)
                    try:
                        uline = line.decode('latin-1')
                    except:
                        self.log("decoding the line using latin-1 has failed. trying errors='ignore' from now on.", 2)
                        try:
                            uline = line.decode('utf-8', errors='ignore')
                        except:
                            self.log("how the fuck did you manage to crash line.decode('utf-8', errors='ignore')? now if decode('ascii', errors='ignore') fails, it's clearly your fault.", 2)
                            uline = line.decode('ascii', errors='ignore')
            if(uline):
                self._messageReceived("console", uline)

    def _messageReceived(self, sender, text):
            for f in self._textCallback:
                f(sender, text)

    def sendTextMessage(self, text):
        print(text.encode(self._encoding, errors='ignore'))
