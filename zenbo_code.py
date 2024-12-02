
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

host = '172.20.10.11'
url = "https://deep-generally-shrew.ngrok-free.app"
transcribe_url = url + "/transcribe"
response_url = url + "/generate_response"
process_audio_url = url + "/process_audio"
emotion_text_url = url + "/detect_emotion"


from pyzenbo.modules.dialog_system import RobotFace
zenbo = pyzenbo.connect(host)

record_audio_file = None

def exit_function():
  zenbo.system.unregister_screen_touch_event(event_type=1, value=1)
  zenbo.robot.set_expression(RobotFace.DEFAULT)
  zenbo.release()
  time.sleep(1)
  
def on_result_callback(**kwargs):
  global record_audio_file
  # If the user touches the screen, record audio
  if kwargs.get('cmd') == commands.SYSTEM_SCREEN_TOUCH_EVENT_REGISTER and kwargs.get('result').get('SCREEN_POINTER_COUNT') == 1 :
    def job():
      # Record audio for 6 seconds, then stop recording
      global record_audio_file

      # Sync is set to False so the robot can show a different expression while recording audio
      zenbo.media.record_audio(duration = 6, sync = False)

      # Set wheel lights and make the robot look interested during recording
      zenbo.robot.set_expression(RobotFace.INTERESTED)
      zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x000000ff)
      zenbo.wheelLights.start_strobing(wheel_lights.Lights.SYNC_BOTH, wheel_lights.Speed.SPEED_DEFAULT)

      time.sleep(int(5))
      zenbo.media.stop_record_audio()

      # Set wheel lights to static and make the robot look lazy after recording
      zenbo.wheelLights.start_static(wheel_lights.Lights.SYNC_BOTH)
      zenbo.robot.set_expression(RobotFace.LAZY)

      time.sleep(int(1))
      print(record_audio_file)
    t = threading.Thread(target=job)
    t.start()
  if kwargs.get('cmd') == commands.MEDIA_RECORD_AUDIO or (kwargs.get('cmd') == commands.MEDIA_STOP_RECORD_AUDIO and '.aac' in kwargs.get('result').get('file')):
    # If the user stops recording audio, send the audio file to the server and process it
    record_audio_file = kwargs.get('result').get('file')
    print(f"record_audio_file: {record_audio_file}")
    if record_audio_file is not None and kwargs.get('cmd') == commands.MEDIA_STOP_RECORD_AUDIO:
        file_path, file_name = os.path.split(record_audio_file)

        # file_transmission to send the audio file to the server so we can process it
        zenbo.media.file_transmission(f'{file_name}')

        # Convert aac to mp3  
        aac_audio = AudioSegment.from_file(f"{file_name}", format="aac")
        aac_audio.export(f"{file_name[:-4]}.mp3", format="mp3")

        # Send the audio file to the server to transcribe it and generate a response using Llama 3.2
        with open(f'{file_name}', "rb") as f:
            response = requests.post(process_audio_url, files={"file": f})
        # Extract the transcription and the response from the server's response
        text_response = response.json()['llama_response'][-1]['content']
        transcription_response = response.json()['transcription']

        # Send the transcription to the server to detect the emotion in the text
        response = requests.post(emotion_text_url, json=str(transcription_response))  
        emotion = response.json()["emotion"]

        # Print the emotion detected and make the robot speak the detected emotion
        print(emotion)
        zenbo.robot.set_expression(RobotFace.PREVIOUS, emotion)

        #zenbo.robot.set_expression(RobotFace.PREVIOUS, response, {'speed':zenbo_speakSpeed, 'pitch':zenbo_speakPitch, 'languageId':zenbo_speakLanguage} , sync = True)
        zenbo.robot.set_expression(RobotFace.PREVIOUS, text_response)
        time.sleep(int(1))
zenbo.robot.set_expression(RobotFace.DEFAULT)
time.sleep(int(0.5))
zenbo.on_result_callback = on_result_callback
zenbo.system.register_screen_touch_event(event_type=1, value=1)
time.sleep(int(1))

# Just some basic robot movements and expressions to show that the robot is ready to interact
zenbo.motion.move_body(0.15, speed_level = 2, sync = True)
zenbo.motion.move_head(pitch_degree = 20, speed_level = 2, sync = True)
zenbo.robot.set_expression(RobotFace.SHY_ADV)
zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x00ffff00)
zenbo.wheelLights.start_strobing(wheel_lights.Lights.SYNC_BOTH, wheel_lights.Speed.SPEED_DEFAULT)
zenbo.utility.track_face(False, False)
try:
  while True:
    time.sleep(int(10))
finally:
  exit_function()
