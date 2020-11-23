import pyttsx3
import socket
import logging
import sys
import threading
import queue
import TTS

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

		self.channel = "#xcomreborn"

		self.ttsReady = threading.Event()
		self.ttsReady.set()

		self.mytts = ttsSpeech(ttsReady=self.ttsReady)
		self.mytts.start()

		self.myDefaultVoiceNumber = 0

		

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

		self.irc.send(('JOIN ' + self.channel + '\r\n').encode("utf8"))

	def run(self):
		self.running = True
		self.irc.setblocking(0)	
		readbuffer = ""
		while self.running:
			try:
				readbuffer= readbuffer+self.irc.recv(1024).decode("utf-8")
				temp=str.split(readbuffer, "\n")
				readbuffer=temp.pop( )
				for line in temp:
					print(line)
					value = line.split()
					if (len(value) >= 5) and (value[2] == "PRIVMSG"):
						userName = value[1]
						userName = userName[1:]
						userName = userName.split("!")[0]
						message = " ".join(value [4:])
						message = message[1:]
						print("user : {0} , message {1}".format(userName, message))
						self.CheckForUserCommand(userName, message)

					if(value[0]=="PING"):
							self.irc.send(("PONG %s\r\n" % line[0]).encode("utf8"))

			except:
				pass
		self.irc.close()

	def CheckForUserCommand(self, userName, message):
		if (userName == "xcomreborn"):
			if (message == "exit"):
				self.mytts.queue.put(message)
				self.running = False
		voices = self.mytts.tts.engine.getProperty('voices')
		if voices:
			print("number of available voices {}".format(len(voices)))
			# create a unique number from the userName string
			mybytearray = bytearray(userName, 'utf-8')
			myint = int.from_bytes(mybytearray, byteorder='big', signed=False)
			# use modulo to define that number from the remainder divison of the number of available voices thus permanently assigning 
			self.myDefaultVoiceNumber = myint%len(voices)
			print("user {} : default voice number {} ".format(userName, self.myDefaultVoiceNumber))

		# testing iteration of voices
		#self.myDefaultVoiceNumber += 1
		#if self.myDefaultVoiceNumber >= len(voices):
		#	self.myDefaultVoiceNumber = 0
		userName = self.processUsername(userName)
		self.mytts.queue.put(messageObject(userName=userName, message=message, voiceNumber=self.myDefaultVoiceNumber))

		
		print("number of threads {0}".format(threading.active_count()))


	def processUsername(self, userName):
		userName = str(userName).replace("_", " ")
		return userName

			
class messageObject():

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
					print ("{} said , {} : voice {}".format(message.userName, message.message, message.voiceNumber))
					self.tts.say("{} said , {}".format(message.userName, message.message))
					self.ttsReady.clear()
		print("exiting tts")
	

# The program propper starts here

myNewBot = IRCBot()
myNewBot.start()