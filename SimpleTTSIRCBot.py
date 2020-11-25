import pyttsx3 
import socket # for creating the network socket connection to twitch server for IRC chat
import logging # for logging errors to file
import sys # for file input and output
import threading # for the creation of separate threads to do several things at once while one thread is buzy
import queue # for inter thread communication
import TTS # wrapper for the pyttsx3 package
import json # for saving and loading to json files
import os # for operating system functions
import re # for regular expressions
import collections # for deque
import jsonpickle # allows saving and reloading of the twitchUser object list to file in json format

for handler in logging.root.handlers[:]:
	logging.root.removeHandler(handler)
logging.basicConfig(format='%(asctime)s (%(threadName)-10s) [%(levelname)s] %(message)s', filename= 'errors.log',filemode = "w", level=logging.INFO)


#
#
# The pyttsx3 package did not work on python 3.8 but appears to work on pyttsx version 2.90 and python version 3.9.0
#
#
class IRCBot(threading.Thread):

	def __init__(self):

		threading.Thread.__init__(self)

		self.server = 'irc.twitch.tv'
		self.port = 6667

		self.nick = 'COHopponentBot'
		self.password = "oauth:6lwp9xs2oye948hx2hpv5hilldl68g"

		self.broadcasterName = "xcomreborn"
		self.channel = "#xcomreborn"

		self.ttsReady = threading.Event()
		self.ttsReady.set()

		self.mytts = ttsSpeech(ttsReady=self.ttsReady)
		self.mytts.start()

		self.blacklist = BlackList()
		self.blacklist.load()


		self.users = twitchUsers()
		self.users.load()

		# create message buffer for out going messages
		self.ircMessageBuffer = collections.deque()
		
		#Set main loop flag
		self.running = True

		#create IRC socket
		try:
			self.irc = socket.socket()
			self.irc.connect((self.server, self.port))
		except Exception as e:
			logging.error("A problem occurred creating a socket")
			logging.error("In IRCBot")
			logging.error(str(e))
			self.irc.close()
			sys.exit(0)

		#sends variables for connection to twitch chat
		self.irc.send(('PASS ' + self.password + '\r\n').encode("utf8"))
		self.irc.send(('USER ' + self.nick + '\r\n').encode("utf8"))
		self.irc.send(('NICK ' + self.nick + '\r\n').encode("utf8"))
		self.irc.send(('CAP REQ :twitch.tv/membership' + '\r\n').encode("utf8")) # sends a twitch specific request necessary to recieve mode messages
		self.irc.send(('CAP REQ :twitch.tv/tags'+ '\r\n').encode("utf8")) # sends a twitch specific request for extra data contained in the PRIVMSG changes the way it is parsed
		self.irc.send(('CAP REQ :twitch.tv/commands' + '\r\n').encode("utf8")) # supposidly adds whispers

		# Start checking send buffer every 3 seconds.
		self.CheckIRCSendBufferEveryThreeSeconds() # only call this once.	


	def run(self):
		
		self.irc.setblocking(0)	

		timeoutTimer = threading.Timer(5, self.connectionTimedOut)
		timeoutTimer.start()
		# add in join timeout
		self.irc.send(('JOIN ' + self.channel + '\r\n').encode("utf8"))

		readbuffer = ""
		while self.running:
			try:
				readbuffer= readbuffer+self.irc.recv(1024).decode("utf-8")
				temp=str.split(readbuffer, "\n")
				readbuffer=temp.pop( )
				for line in temp:
					print(line)
					word = line.split()
					if (len(word) >= 5) and (word[2] == "PRIVMSG"):
						userName = word[1]
						userName = userName[1:]
						userName = userName.split("!")[0]
						message = " ".join(word [4:])
						message = message[1:]
						isMod = bool(int(self.find_between(word[0], "mod=" , ";"))) # returns true if 1 false if 0
						print("user : {} , message {} , is_mod {}".format(userName, message, isMod))
						if isMod or (userName == self.broadcasterName):
							self.checkForModCommand(userName, message) # check for mod user commands
						self.CheckForUserCommand(userName, message) # check for standard user commands
						self.sendToTextToSpeech(userName, message) # process messages for text to speech


					if (len(word) >= 3) and ("JOIN" == word[1]) and (":"+self.nick.lower()+"!"+self.nick.lower()+"@"+self.nick.lower()+".tmi.twitch.tv" == word[0]):
						#cancel auto closing the thread
						logging.info("Joined {} sucessfully.".format(self.channel))
						timeoutTimer.cancel()

					if(word[0]=="PING"):
							self.irc.send(("PONG %s\r\n" % line[0]).encode("utf8"))

			except:
				pass
		self.irc.close() # close the socket
		self.close() # close the program

	def connectionTimedOut(self):
		logging.info("Connection joining {} timed out.".format(self.channel))
		self.close()

	def close(self):
		self.running = False
		self.blacklist.save() # save the blacklist to file
		self.users.save() # save custom voices to file
		logging.info("in close in thread")
		try:
			# send closing message immediately
			self.irc.send(("PRIVMSG " + self.channel + " :" + str("closing opponent bot") + "\r\n").encode('utf8'))
		except Exception as e:
			logging.error("In close")
			logging.error(str(e))



	def CheckIRCSendBufferEveryThreeSeconds(self):
		if (self.running == True): 
			threading.Timer(3.0, self.CheckIRCSendBufferEveryThreeSeconds).start()
		self.IRCSendCalledEveryThreeSeconds()
	# above is the send to IRC timer loop that runs every three seconds
	
	def SendPrivateMessageToIRC(self, message):
		self.ircMessageBuffer.append(message)   # removed this to stop message being sent to IRC

	def IRCSendCalledEveryThreeSeconds(self):
		if (self.ircMessageBuffer):
			try:
				message = self.ircMessageBuffer.popleft()
				self.irc.send(("PRIVMSG " + self.channel + " :" + str(message) + "\r\n").encode('utf8'))
				self.sendToTextToSpeech(self.nick, message) # loopback for text to speech if needed but user will likely be added to ingnore anyway.
			except Exception as e:
				logging.error("IRC send error:")
				logging.error("In IRCSendCalledEveryThreeSeconds")
				logging.error(str(e))
	#above is called by the timer every three seconds and checks for items in buffer to be sent, if there is one it'll send it

	def checkForModCommand(self,userName, message):
		wordList = message.split()

		if (userName == self.broadcasterName):
			if (message == "exit"):
				print("Trying to exit.")
				self.mytts.queue.put(message)
				self.running = False		

		if wordList:
		
			if wordList[0].lower() == "!voices":
				self.SendPrivateMessageToIRC(self.getVoicesAvailableString())
			if (wordList[0].lower() == "!blacklist") or (wordList[0].lower() == "!ignorelist"):
				self.listIgnore()

		if len(wordList) > 1:
			if wordList[0] == "!ignore":
				self.blacklist.addUser(wordList[1]) # check if user was added.
				self.blacklist.save() # save to file.			
			if wordList[0] == "!unignore":
				self.blacklist.removeUser(wordList[1]) # check that user existed and was removed.
				self.blacklist.save() # save to file.

			if wordList[0] == "!voice":
				self.setVoice(userName, message)

			if wordList[0] == "!alias":
				self.setAlias(userName, message)

			if (wordList[0] == "!speed") or (wordList[0] == "!voicespeed"):
				self.setSpeed(userName, message)

	def setSpeed(self, userName, message):
		wordList = message.split()
		speedNumber = 200
		if len(wordList) > 1:
			speed = wordList[1]
			try:
				speedNumber = int(speed)
			except Exception as e:
				logging.info(str(e))
				logging.info("User message {} , value {} was not an int".format(message, speed))
				try:
					speeds = {
					'slowest' : 100,
					'slower' : 150,
					'slow' : 180,
					'normal' : 200,
					'fast' : 220,
					'faster' : 250,
					'fastest' : 300,
					}
					speedNumber = speeds.get(speed.lower())
				except Exception as e:
					logging.info("problem setting string {} to a defined speed {}.".format(speed, str(speeds)))
					return
				lowerRange = 100
				upperRange = 300
				speedsString = ""
				for key in speeds:
					speedsString += " {} ".format(key)
				if not (100 <= speedNumber <= 300):
					self.SendPrivateMessageToIRC("The value {} is outside the allowed range. It should be between {} and {} or one of the following : {}.".format(speed, lowerRange, upperRange, speedsString))
					return # returns because speedNumber is outside range.

				if len(wordList) > 2:
					userName = self.escape(wordList[2]) # switches userName with second input.
				user = self.users.getUser(userName)
				if user:
					user.voiceRate = speedNumber
				else:
					self.users.addUser(userName, voiceRate=speedNumber)
				self.SendPrivateMessageToIRC("{}'s voice rate has been set to {}, ({})".format(userName, speed, speedNumber))
				self.users.save() # save user data to file.

	def setAlias(self, userName, message):
		wordList = message.split()
		if len(wordList) > 1:
			alias = self.escape(wordList[1])
			if len(wordList) > 2:
				userName = self.escape(wordList[2]) # switches userName with second input.
			user = self.users.getUser(userName)
			if user:
				user.alias = alias
			else:
				self.users.addUser(userName, alias=alias)
			self.SendPrivateMessageToIRC("{}'s alias has been set to {}".format(userName, alias))
			self.users.save() # save user data to file.

	def escape(self, mystring):
		mystring = mystring.replace("'","").replace('"',"").replace("\\","") # remove inverted commas and backslash escapes from user input.
		return mystring

	def setVoice(self, userName, message):
		wordList = message.split()
		if len(wordList) > 1:
			numberString = wordList[1]
			if len(wordList) > 2:
				userName = self.escape(wordList[2]) # switches userName with second input.
			try:
				voiceNumber = int(numberString) - 1
			except Exception as e:
				logging.error(str(e))
				self.SendPrivateMessageToIRC("!voice # must be a number")
				return
			voices = self.mytts.tts.engine.getProperty('voices')
			if voices:
				if voiceNumber > len(voices) -1:
					self.SendPrivateMessageToIRC("!voice # must be less than {}.".format(str(len(voices))))
					return
				if voiceNumber < 0:
					self.SendPrivateMessageToIRC("!voice # cannot be less than 0.")
					return
			user = self.users.getUser(userName)
			if user:
				user.voiceNumber = voiceNumber
			else:
				self.users.addUser(userName, voiceNumber=voiceNumber)
			try:
				self.SendPrivateMessageToIRC("{}'s voice has been set to {}".format(userName, int(voiceNumber) + 1))
				self.users.save() # save user data to file
			except Exception as e:
				logging.error(str(e))


	def getVoicesAvailableString(self):
		try:
			voices = self.mytts.tts.engine.getProperty('voices')
			outputString = "Voices available : {} :".format(len(voices))
			for idx,item in enumerate(voices):
				if isinstance(item, pyttsx3.voice.Voice):
					outputString += " #{} {}".format(str(idx + 1), str(item.name)) 
			return outputString
		except Exception as e:
			logging.error(str(e))
			return "Could not get voices."

	def CheckForUserCommand(self, userName, message):
		wordList = message.split()
		if wordList:
			#if wordList[0].lower() == "!ignoreme": # add this if you want users to be able to add themselves to the blacklist
			#	self.blacklist.addUser(userName)
			pass


	def sendToTextToSpeech(self, userName, message):
		try:
			voices = self.mytts.tts.engine.getProperty('voices')
			myDefaultVoiceNumber = 0
			voiceRate = 200
			if voices:
				# create a unique number from the userName string.
				mybytearray = bytearray(userName, 'utf-8')
				myint = int.from_bytes(mybytearray, byteorder='big', signed=False)
				# use modulo to define that number from the remainder divison of the number of available voices thus permanently assigning.
				myDefaultVoiceNumber = myint%len(voices)
				print("user {} : default voice number {} ".format(userName, myDefaultVoiceNumber))

			ignoredUserNames = self.blacklist.users # gets current blacklist.
			if userName.lower() not in map(str.lower, ignoredUserNames):
				userName = self.preprocessUsername(userName)
				message = self.preprocessMessage(message)
				messageAllowed = self.isMessageAllowed(message)
				if messageAllowed:
					if self.users.isUserInList(userName):
						user = self.users.getUser(userName)
						if user.voiceNumber:
							myDefaultVoiceNumber = int(user.voiceNumber) # set the saved voice number if it exists.
						if user.alias:
							userName = user.alias # set username to be spoken to alias if it exists.
						if user.voiceRate:
							voiceRate = user.voiceRate # set voiceRate to be spoken if it exists.
					if not isinstance(myDefaultVoiceNumber, int):
						return
					if myDefaultVoiceNumber > (len(voices) -1):
						return
					if myDefaultVoiceNumber < 0:
						return
					
					self.mytts.queue.put(messageObject(userName=userName, message=message, voiceNumber=myDefaultVoiceNumber, voiceRate=voiceRate))
			print("number of threads {0}".format(threading.active_count()))
		except Exception as e:
			logging.error(str(e))


	def preprocessUsername(self, userName):
		userName = str(userName).replace("_", " ") # replaces underscore with space
		return userName

	def preprocessMessage(self, message):
		message  = str(message).replace("_", " ") # replaces underscore with space
		#implement character removals etc here.
		return message

	def isMessageAllowed(self, message):
		# a series of conditions to test against if they appear return False (message rejected)
		if message:
			if message[0] == "!" or message[0] == "#":
				return False
		if "http" in message:
			return False
		
		return True

	def listIgnore(self):
		ignoredList = self.blacklist.users
		outputString = ""
		if ignoredList:
			outputString += "Text to speech ignored users : "
			for item in ignoredList:
				outputString += " {}".format(str(item))
			self.SendPrivateMessageToIRC(outputString)
		else:
			self.SendPrivateMessageToIRC("There are no users in the TTS blacklist.")

	def find_between(self, s, first, last ):
		try:
			start = s.index( first ) + len( first )
			end = s.index( last, start )
			return s[start:end]
		except ValueError:
			return ""

class BlackList():
	def __init__(self):
		self.users = []

	def addUser(self, userName):
		self.users.append(self.escape(userName))
		self.users = list(set(self.users))
		#ensure all users are unique

	def removeUser(self, userName):
		try:
			self.users.remove(userName)
			return True # success
		except Exception as e:
			logging.error(str(e))
			return False # user not in list

	def escape(self, mystring):
		mystring = mystring.replace("'","").replace('"',"").replace("\\", "") # remove inverted commas and backslash escapes from user input
		return mystring

	def load(self):
		try:
			if (os.path.isfile('blacklist.json')):
				with open('blacklist.json') as json_file:
					data = json.load(json_file)
					self.users = list(data)
					logging.info("data loaded sucessfully")

		except Exception as e:
			logging.error("Problem in load")
			logging.error(str(e))

	def save(self):
		try:
			with open('blacklist.json' , 'w') as outfile:
				json.dump(self.users, outfile)
		except Exception as e:
			logging.error("Problem in save")
			logging.error(str(e))


class twitchUsers():

	def __init__(self):
		self.users = []

	def removeUser(self, userName):
		if self.isUserInList(userName):
			newList = []
			for item in self.users:
				if isinstance(item, chatUser):
					if item.userName != userName:
						newList.append(item)
			self.users = newList
			return True # success
		else:
			return False # user not in list

	def addUser(self, userName, alias = None,voiceNumber = None, voiceRate = 200):
		if self.isUserInList(userName):
			return False
		else:
			self.users.append(chatUser(userName, alias=alias,voiceNumber=voiceNumber, voiceRate=voiceRate))
			return True

	def special_match(self, strg, search=re.compile(r'^[a-zA-Z0-9][\w]{3,24}$').search):
		if strg == "":
			return True
		return bool(search(strg))

	def getUser(self, userName):
		for item in self.users:
			if isinstance(item, chatUser):
				if item.userName == userName:
					return item
		return None

	def isUserInList(self, userName):
		success = False
		for item in self.users:
			if isinstance(item, chatUser):
				if item.userName == userName:
					success = True
		return success

	def load(self):
		try:
			if (os.path.isfile('data.json')):
				with open('data.json') as json_file:
					data = json.load(json_file)
					self.users = jsonpickle.decode(data)
					logging.info("data loaded sucessfully")
		except Exception as e:
			logging.error("Problem in load")
			logging.error(str(e))

	def save(self):
		try:
			objectToDump = jsonpickle.encode(self.users)
			with open('data.json' , 'w') as outfile:
				json.dump(objectToDump, outfile)
		except Exception as e:
			logging.error("Problem in save")
			logging.error(str(e))


class chatUser():
	# This class is used to hold a permanent record of the chat user in memory if they are ignored or their voice has changed for the auto assigned default 
	def __init__(self, userName = None, alias = None,voiceNumber = None, voiceRate = 200):
		self.userName = userName
		self.alias = alias
		self.voiceNumber = voiceNumber
		self.voiceRate = voiceRate

	def __str__(self):
		return "userName : {}  alias : {}  voiceNumber : {}  voiceRate {}".format(self.userName, self.alias, self.voiceNumber, self.voiceRate)

	def __repr__(self):
		return str(self)


class messageObject():
	# This class is used as a data structure to send to the text to speech class

	def __init__(self, userName = None, message = None, voiceNumber = 0, voiceRate = 200):
		self.userName = userName
		self.message = message
		self.voiceNumber = voiceNumber
		self.voiceRate = voiceRate


class ttsSpeech(threading.Thread):

	def __init__(self, ttsReady = None):
		self.ttsReady = ttsReady
		threading.Thread.__init__(self)
		self.queue = queue.Queue()
		self.tts = TTS.TTSThread(ttsReady = self.ttsReady)
		self.previousUserName = ""

	def run(self):

		messageStack = []
		while (True):
			try:
				messageStack.append(self.queue.get(block=False))
			except:
				pass
			#print("is set {} and len messagestack {}".format(str(self.ttsReady.is_set()), str(len(messageStack))))

			if (self.ttsReady.is_set()) and len(messageStack) > 0:
				message = messageStack.pop(0)
				print("recived {}".format(message))
				if message == "exit":
					self.tts.terminate()
					break
				if isinstance(message, messageObject):
					voices = self.tts.engine.getProperty('voices')
					self.tts.engine.setProperty('voice',voices[message.voiceNumber].id)
					self.tts.engine.setProperty('rate', message.voiceRate)
					print ("{} said , {} : voice {}".format(message.userName, message.message, message.voiceNumber))

					if (self.previousUserName.lower() == message.userName.lower()):
						self.tts.say(message.message)
					else:
						self.tts.say("{} said , {}".format(message.userName, message.message))

					self.previousUserName = message.userName
					self.ttsReady.clear()
		print("exiting tts")
	

# The program propper starts here

myNewBot = IRCBot()
myNewBot.start()