# TTS.py
import threading, time, pyttsx3


class TTSThread(threading.Thread):
    def __init__(self, ttsReady = None, rate=115, event=None):
        super().__init__()

        if event:
            setattr(self, event, threading.Event())

        self.ttsReady = ttsReady
        
        self._cancel = threading.Event()
        self.rate = rate
        self.engine = None

        self._say = threading.Event()
        self._text_lock = threading.Lock()
        self._text = []

        self._is_alive = threading.Event()
        self._is_alive.set()
        self.start()

    def _init_engine(self, rate):
        engine = pyttsx3.init()
        engine.setProperty('rate', rate)  # setting up new voice rate    
        engine.connect('finished-utterance', self._on_completed)
        engine.connect('started-word', self._on_cancel)
        return engine

    def say(self, text, stop=None):
        if self._is_alive.is_set():
            self._cancel.clear()

            if isinstance(text, str):
                text = [(text, stop)]

            if isinstance(text, (list, tuple)):
                for t in text:
                    if isinstance(t, str):
                        t = t, None

                    with self._text_lock:
                        self._text.append(t)

                    self._say.set()

    def cancel(self):
        self._cancel.set()

    def _on_cancel(self, name, location, length):
        if self._cancel.is_set():
            self.stop()

    def stop(self):        
        self.engine.stop()
        time.sleep(0.5)
        self.engine.endLoop()

    def _on_completed(self, name, completed):
        if completed:
            self.engine.endLoop()
            self.on_finished_utterance(name, completed)

    def on_finished_utterance(self, name, completed):
        print("on_finished_utterance was called") 
        print(self.ttsReady)
        if self.ttsReady:
            self.ttsReady.set()
            print ("ttsReady was set to {}".format(str(self.ttsReady.is_set())))
        self.engine.endLoop()

    def terminate(self):
        self._is_alive.clear()
        self._cancel.set()
        self.join()

    def run(self):
        self.engine = engine = self._init_engine(self.rate)
        while self._is_alive.is_set():
            while self._say.wait(0.1):
                self._say.clear()

                while not self._cancel.is_set() and len(self._text):
                    with self._text_lock:
                        engine.say(*self._text.pop(0))
                    engine.startLoop()

class Voice(TTSThread):
    def __init__(self):
        self.completed = None
        super().__init__(rate=115, event='completed')

    def on_finished_utterance(self, name, completed):
        print("utterance finished")
        self.completed.set()
