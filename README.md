# SimplePythonTTSBot
A simple partial implementation of the IRC protocol for twitch chat made in python with Text To Speach for readout

This python bot requires the following non standard python packages to be installed.

pyttsx3

This can be installed on the command line using "pip install pyttsx3"

pyttsx3 Text to Speech (TTS) library for Python 2 and 3. Works without internet connection or delay. Supports multiple TTS engines, including Sapi5, nsss, and espeak.

jsonpickle

This can be installed on the command line using "pip install jsonpickle"

This bot was written and tested on Windows 10 (Using espeak/SAPI5), and uses the Microsoft Voices accessible publicly in the language options.

eSpeak was available at http://espeak.sourceforge.net/

At time of writting it was possible to unlock more microsoft voices using the method detailed by this third party site:

https://www.ghacks.net/2018/08/11/unlock-all-windows-10-tts-voices-system-wide-to-get-more-of-them/


The bot commands are restricted to twitch channel moderators and are as follows:

!voices - lists all available voices
!voice # - sets the users voice to an available voice listed in !voices

!ignore [] - ignores the following user name
!unignore [] - unignores the following user name
!blacklist - lists all the usernames in the blacklist (ignorelist)


