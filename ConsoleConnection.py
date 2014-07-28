import AbstractConnection
import sys
import string


class ConsoleConnection(AbstractConnection.AbstractConnection):
    def __init__(self, encoding, name, loglevel):
        """
        just store the encoding.
        """
        super(ConsoleConnection, self).__init__(name, loglevel)
        self._encoding = encoding

    def _openConnection(self):
        """
        there is nothing to open; all we need is stdout/stdin.
        """
        return True

    def _initConnection(self):
        """
        nothing to do here either.
        """
        return True

    # no need to overload _postConnect either.

    def _closeConnection(self):
        """
        closing is a no-op, too.
        """
        return True

    def _try_decode_as_hard_as_possible(self, line):
        """
        console input can be hard to decode. seriously.
        """
        try:
            return line.decode(self._encoding)
        except:
            self._logException("failed decoding as " + self._encoding, 1)

        try:
            return line.decode('utf-8')
        except:
            self._logException("failed decoding as utf-8", 1)

        try:
            return line.decode('latin-1')
        except:
            self._logException("failed decoding as latin-1", 1)

        try:
            return line.decode('utf-8', errors='ignore')
        except:
            # how could this even happen
            self._logException("failed decoding as utf-8, ignoring errors",
                               1)

        try:
            return line.decode('ascii', errors='ignore')
        except:
            # last chance, seriously
            self._logException("failed decoding as ascii, ignoring errors"
                               1)

        return "[decoding error]"

    def _listen(self):
        """
        read data from stdin, and interpret it as a chat message
        """
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            self._log("keyboard interrupt", 1)
            self._invokeTextCallback("console", "Goodbye.")
            return False

        line = self._try_decode_as_hard_as_possible(line)
        self._invokeTextCallback("console", line)
        return True

    # send the given line to stdout.
    def _sendMessageUnsafe(self, message):
        """
        write the message to stdout
        """
        print(message.encode(self._encoding, errors='ignore'))
        return True

    # pass the given line to _sendMessage.
    def _sendTextMessageUnsafe(self, message):
        """
        text messages are just written as they are, no need to add a header
        """
        return self._sendMessage(message)
