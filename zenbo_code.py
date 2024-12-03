
from decimal import *
from pydub import AudioSegment
import os
import sys
# Append cwd
sys.path.append(os.getcwd())
from pyzenbo.modules import wheel_lights
import threading
import pyzenbo
import pyzenbo.modules.zenbo_command as commands
import time
import requests
from pyzenbo.modules.dialog_system import RobotFace

# Zenbo IP
host = '172.20.10.11'
# ngrok URL from the server
url = "https://deep-generally-shrew.ngrok-free.app"

# API Endpoints (can be found in the line above each API endpoint in zenbo_api.py)
transcribe_url = url + "/transcribe"
response_url = url + "/generate_response"
process_audio_url = url + "/process_audio"
emotion_text_url = url + "/detect_emotion"

zenbo_speakSpeed = 100
zenbo_speakPitch = 100

# Connect to Zenbo
zenbo = pyzenbo.connect(host)

# Keeps track of the audio recording file and the conversation up to that point
record_audio_file = None
conversation = []

# Gets called when the program is exited
def exit_function():
  zenbo.system.unregister_screen_touch_event(event_type=1, value=1)
  zenbo.robot.set_expression(RobotFace.DEFAULT)
  zenbo.release()
  time.sleep(1)

# Gets called when a result is returned from Zenbo, for now it only handles the audio recording.
def on_result_callback(**kwargs):
  global zenbo_speakSpeed, zenbo_speakPitch, record_audio_file
  if kwargs.get('cmd') == commands.SYSTEM_SCREEN_TOUCH_EVENT_REGISTER and kwargs.get('result').get('SCREEN_POINTER_COUNT') == 1 :
    pass
  if kwargs.get('cmd') == commands.MEDIA_RECORD_AUDIO or (kwargs.get('cmd') == commands.MEDIA_STOP_RECORD_AUDIO and '.aac' in kwargs.get('result').get('file')):
    record_audio_file = kwargs.get('result').get('file')

# Records audio, sends it to the server for processing, and generates a response+emotion.
def record_audio_and_respond():
    # Record audio, sync = False to allow for other commands to be executed while recording (e.g changing the emotion of Zenbo)
    zenbo.media.record_audio(duration = 6, sync = False)
    time.sleep(int(5))

    # Set the wheel lights to strobing to indicate that Zenbo is listening, also set the expression to interested
    zenbo.robot.set_expression(RobotFace.LAZY_ADV)
    zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x000000ff)
    zenbo.wheelLights.start_strobing(wheel_lights.Lights.SYNC_BOTH, wheel_lights.Speed.SPEED_DEFAULT)

    # Stop recording audio, and set the wheel lights to static
    zenbo.media.stop_record_audio()
    zenbo.wheelLights.start_static(wheel_lights.Lights.SYNC_BOTH)

    print(f"record_audio_file: {record_audio_file}")
    # If the audio file is not None, send it to the server for processing
    if record_audio_file is not None: 
        file_path, file_name = os.path.split(record_audio_file)
        
        # Sends the audio file from zenbo to the server so it can be processed
        zenbo.media.file_transmission(f'{file_name}')

        # Convert aac to mp3
        aac_audio = AudioSegment.from_file(f"{file_name}", format="aac")
        aac_audio.export(f"{file_name[:-4]}.mp3", format="mp3")

        # Read the audio file and transcribe it, + generate a response.
        with open(f'{file_name[:-4]}.mp3', "rb") as f:
            process_response = requests.post(process_audio_url, files={"file": f, "conversation": str(conversation)})

        # Get the responses from the API
        text_response = process_response.json()['llama_response'][-1]['content']
        transcription_response = process_response.json()['transcription']

        # Keep track of the conversation
        conversation.append({'user': transcription_response, 'zenbo': text_response})

        # Get the emotion of the user's response and make Zenbo say it
        emotion_response = requests.post(emotion_text_url, json=str(transcription_response))  
        emotion = emotion_response.json()["emotion"]
        print(emotion)
        zenbo.robot.set_expression(RobotFace.PREVIOUS, emotion)

        # Make Zenbo say the response to what the user said
        zenbo.robot.set_expression(RobotFace.PREVIOUS, text_response)
        time.sleep(int(0.5))
    time.sleep(0.5)
   

zenbo.robot.set_expression(RobotFace.DEFAULT)
time.sleep(int(0.5))
zenbo.on_result_callback = on_result_callback
zenbo.system.register_screen_touch_event(event_type=1, value=1)
time.sleep(int(1))

# Set the expression to interested and the wheel lights to static
zenbo.motion.move_body(0.15, speed_level = 2, sync = True)
zenbo.motion.move_head(pitch_degree = 20, speed_level = 2, sync = True)
zenbo.robot.set_expression(RobotFace.INTERESTED_ADV)
zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x00ffff00)
zenbo.wheelLights.start_static(wheel_lights.Lights.SYNC_BOTH)
zenbo.utility.track_face(False, False)
zenbo_speakLanguage = 2
zenbo.robot.set_expression(RobotFace.PREVIOUS, 'Hello, my name is Zenbo, I am here to learn about how you are doing this week. Do you have any questions for me?', {'speed':zenbo_speakSpeed, 'pitch':zenbo_speakPitch, 'languageId':zenbo_speakLanguage} , sync = True)

for count in range(5):
    record_audio_and_respond()
exit_function()

try:
  while True:
    time.sleep(int(10))
finally:
  exit_function()
