#!/usr/bin/python2
import sys
import MumbleConnection
import IRCConnection

irc = None
mumble = None

def mumbleTextMessageCallback(sender, message):
	line="mumble: " + sender + ": " + message
	print(line)
	irc.sendTextMessage(line)

def ircTextMessageCallback(sender, message):
	line="irc: " + sender + ": " + message
	print(line)
	mumble.sendTextMessage(line)

def main():
	global mumble
	global irc

	loglevel = 0

	#create server connections
	mumble = MumbleConnection.MumbleConnection("wue.ensslin.cc", 1337, "Neger", "sftbot", "robot_enrichment_center", loglevel)
	irc = IRCConnection.IRCConnection("irc.freenode.net", 6667, "sftbot", "sftclan", loglevel)

	mumble.registerTextCallback(mumbleTextMessageCallback)
	irc.registerTextCallback(ircTextMessageCallback)

	while True:
		try:
			line = sys.stdin.readline()
		except KeyboardInterrupt:
			print("interrupted.")
			break

		if(line):
			line = "console: " + line
			mumble.sendTextMessage(line) 
			irc.sendTextMessage(line)

if __name__=="__main__":
	main()
