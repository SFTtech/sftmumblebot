#!/usr/bin/python2
import sys
import MumbleConnection
import IRCConnection

def textCallback(sender, message):
	print(sender + ": " + message);

def main():
	mc = MumbleConnection.MumbleConnection("wue.ensslin.cc", 1337, "Neger", "timebot", "robot_enrichment_center", 0)
	mc.registerTextCallback(textCallback)
	mc.connectToServer()

	ic = IRCConnection.IRCConnection("irc.freenode.net", 6667, "sftbot", "sftclan")

	print("lol")

	while True:
		try:
			line = sys.stdin.readline()
		except KeyboardInterrupt:
			print("interrupted.")
			break

		if(line):
			mc.sendTextMessage(line) 

if __name__=="__main__":
	main()
