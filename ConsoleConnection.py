import AbstractConnection
import sys
import string

class ConsoleConnection(AbstractConnection.AbstractConnection):
    # global configuration variables set by the constructor.
    _encoding = None

    # call the superconstructor and set global configuration variables.
    def __init__(self, encoding, name, loglevel):
        super(ConsoleConnection,self).__init__(name, loglevel)
        self._encoding = encoding

    # no need to do anything here.
    def _openConnection(self):
        return True

    # no need to do anything here as well.
    def _initConnection(self):
        return True

    # post-connect, call _connectionEstablished() and return true.
    def _postConnect(self):
        self._connectionEstablished()
        return True

    # no need to do anything here.
    def _closeConnection(self):
        return True

    # read and interpret data from stdin.
    def _listen(self):
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            self._log("keyboard interrupt", 1)
            self._invokeTextCallback("console", "Goodbye.")
            return False

        uline = None
        try:
            uline = line.decode(self._encoding)
        except:
            self._log("decoding the line using the default encoding " + self._encoding + " has failed.", 1)
            try:
                uline = line.decode('utf-8')
            except:
                self._log("decoding the line using utf-8 has failed.", 1)
                try:
                    uline = line.decode('latin-1')
                except:
                    self._log("decoding the line using latin-1 has failed. trying errors='ignore' from now on.", 1)
                    try:
                        uline = line.decode('utf-8', errors='ignore')
                    except:
                        self._log("how the fuck did you manage to crash line.decode('utf-8', errors='ignore')? now if decode('ascii', errors='ignore') fails, it's clearly your fault.", 1)
                        uline = line.decode('ascii', errors='ignore')
        if(uline):
            self._invokeTextCallback("console", uline)
        return True

    # send the given line to stdout.
    def _sendMessageUnsafe(self, message):
        print(message.encode(self._encoding, errors='ignore'))
        return True

    # pass the given line to _sendMessage.
    def _sendTextMessageUnsafe(self, message):
        return self._sendMessage(message)
