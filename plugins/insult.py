class Plugin():
	command = "!insult"

	def __init__(self, mumble, irc):
		self.mumble = mumble
		self.irc = irc
	
	def __call__(self, sender, message, params=[]):
		if len(params) > 1:
			return "I think %s is full of shit." % (params[1],)
		else:
			return "You're full of shit, %s" % (sender,)
