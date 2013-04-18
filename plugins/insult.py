import random

class Plugin():
	command = "!insult"
	insultion_array = [ "Fick du dich %s ", "%s , Fick dich", "%s , deine Mamma lutscht Schwaenze in der Hoelle", "%s benutzt Windows 8" , " You're full of shit %s ", "%s programmiert verteiltes Echtzeit Java", "%s , bitte sterben sie zeitnah", "%s , verrecke in der Hoelle", "Ich werde %s die Augen auskratzen und dann pisse ich in seinen Totenschaedel" , "%s ist nicht ganz so toll wie andere Menschen" , "%s fick dich hinfort", "%s du bist scheisse", "Ich moechte vornehm die Meinung aeussern, dass %s ein dummes Stueck scheisse ist", "%s loves building Web Applications"]
	
	def __init__(self, mumble, irc):
		self.mumble = mumble
		self.irc = irc
        random.seed(88)
	
	def __call__(self, sender, message, params=[]):

 		if len(params) > 1:
 			return random.choice(self.insultion_array) % params[1]
 		else:
 			return random.choice(self.insultion_array) % sender
