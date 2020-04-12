from google.cloud import texttospeech
from playsound import playsound as ps
import time
from datetime import date
import datetime

import pyowm
"""owm = pyowm.OWM('dd61e86e90664667777f2cee9e1ec09c')
la = owm.weather_at_place('Ahmedabad, IN')
w = la.get_weather()
print(w.get_temperature('celsius')['temp'])
temp = w.get_temperature('celsius')['temp']
temp = int(temp)
text = str(temp) + "Degree Celsius"
"""
client = texttospeech.TextToSpeechClient()


voice = texttospeech.types.VoiceSelectionParams(language_code='en-US', ssml_gender=texttospeech.enums.SsmlVoiceGender.FEMALE)

audio_config = texttospeech.types.AudioConfig(audio_encoding=texttospeech.enums.AudioEncoding.MP3)


"""time = datetime.datetime.now()
month = time.strftime("%b")
today = date.today()
day = today.day
hour = time.hour
pm = False
if hour > 11:
    pm = True
hour %= 12
if hour == 0:
    hour = 12

if 4 <= day <= 20 or 24 <= day <= 30:
    suffix = "th"
else:
    suffix = ["st", "nd", "rd"][day % 10 - 1]
string = str(day) + " " + month + ""
string += str(hour) + ":" + str(time.minute)
if pm:
    string += " pm"
else:
    string += " am"
print(string)"""
#text = "Temperature:"
#text = "Good Morning"
#text = "Good Evening"
#text = "Good Night"
text = "Degree Fahrenheit"
synthesis_input = texttospeech.types.SynthesisInput(text=text)
response = client.synthesize_speech(synthesis_input, voice, audio_config)
with open('fahrenheit.mp3', 'wb') as out:
    out.write(response.audio_content)
    print("Written")

ps('fahrenheit.mp3')