import pyttsx3
engine = pyttsx3.init() # object creation

""" RATE"""
rate = engine.getProperty('rate')   # getting details of current speaking rate
print (rate)                        #printing current voice rate
rate = 180
engine.setProperty('rate', rate)     # setting up new voice rate


"""VOLUME"""
volume = engine.getProperty('volume')   #getting to know current volume level (min=0 and max=1)
print (volume)                          #printing current volume level
engine.setProperty('volume',1.0)    # setting up volume level  between 0 and 1

"""VOICE"""
voices = engine.getProperty('voices')       #getting details of current voice
print(len(voices))
print( voices[0]) 
#engine.setProperty('voice', voices[0].id)  #changing index, changes voices. o for male
engine.setProperty('voice', voices[0].id)   #changing index, changes voices. 1 for female


"""Saving Voice to a file"""
# On linux make sure that 'espeak' and 'ffmpeg' are installed
#engine.save_to_file('FractionalEyes : fi : WM : 1v1 Rank 42 : lvl 13', 'test.mp3')
#engine.runAndWait()

engine.say("phrase 1")
#engine.say('FractionalEyes : fi : WM : 1v1 Rank 42 : lvl 13')
engine.runAndWait()
engine.say("Hello World!")
#engine.say('FractionalEyes : fi : WM : 1v1 Rank 42 : lvl 13')
engine.runAndWait()
engine.say("Hello World!")
#engine.say('FractionalEyes : fi : WM : 1v1 Rank 42 : lvl 13')
engine.runAndWait()
engine.say("Hello World!")
#engine.say('FractionalEyes : fi : WM : 1v1 Rank 42 : lvl 13')
engine.runAndWait()

print("run and wait ended apparently.")