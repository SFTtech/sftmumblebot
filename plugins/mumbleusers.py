class Plugin():
	command = "!users"

	def __init__(self, mumble, irc):
		self.mumble = mumble
		self.irc = irc
	
	def __call__(self, sender, message):
		return 'Mumble users: '+' '.join(self.mumble._userIds.keys())
