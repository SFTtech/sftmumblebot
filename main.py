#!/usr/bin/env python2
import sys
import MumbleConnection
import IRCConnection
import ConsoleConnection
import time
import ConfigParser
import os.path

plugins = []
irc = None
mumble = None
console = None

html_color_string_for_sender_name = '<span style="color:brown; font-weight:bold">'
html_color_string_for_irc = '<span style="font-weight:bold">'

conffile = "sftbot.conf"

def handle_plugins(sender, message):
# don't relay messages already handled by any plugins
	handled = False
	result = None
	global plugins
	for plugin in plugins:
		# plugins where command is None want to handle every message
		# if their call methods return None, no message is sent. however
		# they may choose to send messages on their own.
		if plugin.command == None:
			result = plugin(sender, message())
			if result != None:
				handled = True
		elif message.startswith(plugin.command):
			handled = True
			params=message.split(' ')
			result = plugin(sender,message, params=params)
	
	return (handled, result)

def mumbleTextMessageCallback(sender, message):
	handled, result = handle_plugins(sender, message)
	if not handled:
		line="mumble: " + sender + ": " + message
		console.sendTextMessage(line)
		irc.sendTextMessage(line)
	elif result != None:
		mumble.sendTextMessage(result)	

def ircTextMessageCallback(sender, message):
	handled, result = handle_plugins(sender, message)
	
	if not handled:
		line = html_color_string_for_irc + "irc: " + "</span>" + html_color_string_for_sender_name + sender + ": " + "</span>" + message
		console.sendTextMessage(line)
		mumble.sendTextMessage(line)
	elif result != None:
		irc.sendTextMessage(result)	

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
	global plugins

	loglevel = 3

	if not os.path.isfile(conffile):
		raise Exception('configuration file {0} not found or unreadable. fix pls.'.format(conffile))

	#create python's configparser and read our configfile
	cparser = ConfigParser.ConfigParser()
	cparser.read(conffile)
	
	# get a plugin-list from conffile
	plugin_status_tupel_list = cparser.items("plugins") # returns a list of ( parameter, value ) tupels
	
	pluginlist = []
	for tupel in plugin_status_tupel_list:
		if tupel[1] == "True":
			pluginlist.append(tupel[0])
	

	#configuration for the mumble connection
	mblservername = cparser.get('mumble', 'server')
	mblport = int(cparser.get('mumble', 'port'))
	mblnick = cparser.get('mumble', 'nickname')
	mblchannel = cparser.get('mumble', 'channel')
	mblpassword = cparser.get('mumble', 'password')
	mbltokens = cparser.get('mumble', 'tokens').split()
	mblloglevel = int(cparser.get('mumble', 'loglevel'))

	#configuration for the IRC connection
	ircservername = cparser.get('irc', 'server')
	ircport = int(cparser.get('irc', 'port'))
	ircnick = cparser.get('irc', 'nickname')
	ircpassword = cparser.get('irc', 'password')
	ircchannel = cparser.get('irc', 'channel')
	ircencoding = cparser.get('irc', 'encoding')
	ircloglevel = int(cparser.get('irc', 'loglevel'))
	
	
	# create server connections
	#hostname, port, nickname, channel, password, name, loglevel
	mumble = MumbleConnection.MumbleConnection(mblservername, mblport, mblnick, mblchannel, mblpassword, mbltokens, "mumble", mblloglevel)
	irc = IRCConnection.IRCConnection(ircservername, ircport, ircnick, ircpassword, ircchannel, ircencoding, "irc", ircloglevel)
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

	# load activated plugins
	sys.path.append('./plugins')
	for plugin_file in pluginlist :
		plugin = __import__(plugin_file)
		plugins.append(plugin.Plugin(mumble, irc))	


	#use the console as main loop
	console.run()

if __name__=="__main__":
	main()
