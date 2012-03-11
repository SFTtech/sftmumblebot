#!/usr/bin/python2
import sys
import MumbleConnection
import IRCConnection
import ConsoleConnection
import time

irc = None
mumble = None
console = None

def mumbleTextMessageCallback(sender, message):
    line="mumble: " + sender + ": " + message
    console.sendTextMessage(line)
    irc.sendTextMessage(line)
    if(message == 'gtfo'):
        mumble.sendTextMessage("KAY CU")
        mumble.stop()

def ircTextMessageCallback(sender, message):
    line="irc: " + sender + ": " + message
    console.sendTextMessage(line)
    mumble.sendTextMessage(line)
    if (message == 'gtfo'):
        irc.sendTextMessage("KAY CU")
        irc.stop()

def consoleTextMessageCallback(sender, message):
    line="console: " + message
    irc.sendTextMessage(line)
    mumble.sendTextMessage(line)

def mumbleDisconnected():
    line="connection to mumble lost. reconnect in 5 seconds."
    console.sendTextMessage(line)
    irc.sendTextMessage(line)
    time.sleep(5)
    mumble.start()

def mumbleConnectionFailed():
    line="connection to mumble failed. retrying in 15 seconds."
    console.sendTextMessage(line)
    irc.sendTextMessage(line)
    time.sleep(15)
    mumble.start()

def ircDisconnected():
    line="connection to irc lost. reconnect in 15 seconds."
    console.sendTextMessage(line)
    mumble.sendTextMessage(line)
    time.sleep(15)
    irc.start()

def ircConnectionFailed():
    line="connection to irc failed. retrying in 15 seconds."
    console.sendTextMessage(line)
    mumble.sendTextMessage(line)
    time.sleep(15)
    irc.start()


def main():
    global mumble
    global irc
    global console

    loglevel = 3

    # create server connections
    mumble = MumbleConnection.MumbleConnection("wue.ensslin.cc", 1337, "sftbot", "robot_enrichment_center", "Neger", "mumble", loglevel)
    irc = IRCConnection.IRCConnection("irc.freenode.net", 6667, "sftbot", "sftclan", "utf-8", "irc", loglevel)
    console = ConsoleConnection.ConsoleConnection("utf-8", "console", loglevel)

    # register text callback functions
    mumble.registerTextCallback(mumbleTextMessageCallback)
    irc.registerTextCallback(ircTextMessageCallback)
    console.registerTextCallback(consoleTextMessageCallback)	

    # register connection-lost callback functions
    irc.registerConnectionLostCallback(ircDisconnected)
    mumble.registerConnectionLostCallback(mumbleDisconnected)

    # register connection-failed callback functions
    irc.registerConnectionFailedCallback(ircConnectionFailed)
    mumble.registerConnectionFailedCallback(mumbleConnectionFailed)

    # start the connections. they will be self-sustaining due to the callback functions
    mumble.start()
    irc.start()

    #use the console as main loop
    console.run()

if __name__=="__main__":
    main()
