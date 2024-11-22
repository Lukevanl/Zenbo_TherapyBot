
import os
from pydub import AudioSegment
import os
import sys
# Append cwd
sys.path.append(os.getcwd())
import requests
import threading
import pyzenbo
from pyzenbo.modules import wheel_lights
import pyzenbo.modules.zenbo_command as commands
import time
from pyzenbo.modules.dialog_system import RobotFace

host = '172.20.10.11'
ip = "172.20.10.12"
transcribe_url = f"http://{ip}:8000/transcribe"
response_url = f"http://{ip}:8000/generate_response"
process_audio_url = f"http://{ip}:8000/process_audio"

from pyzenbo.modules.dialog_system import RobotFace
zenbo = pyzenbo.connect(host)

zenbo_speakSpeed = 100
zenbo_speakPitch = 100

record_audio_file = None
conversation = []

def exit_function():
  zenbo.system.unregister_screen_touch_event(event_type=1, value=1)
  zenbo.robot.set_expression(RobotFace.DEFAULT)
  zenbo.release()
  time.sleep(1)

def on_result_callback(**kwargs):
  global zenbo_speakSpeed, zenbo_speakPitch, record_audio_file
  if kwargs.get('cmd') == commands.SYSTEM_SCREEN_TOUCH_EVENT_REGISTER and kwargs.get('result').get('SCREEN_POINTER_COUNT') == 1 :
    pass
  if kwargs.get('cmd') == commands.MEDIA_RECORD_AUDIO or (kwargs.get('cmd') == commands.MEDIA_STOP_RECORD_AUDIO and '.aac' in kwargs.get('result').get('file')):
    record_audio_file = kwargs.get('result').get('file')

def record_audio_and_respond():
    zenbo.media.record_audio(duration = 6, sync = False)
    time.sleep(int(5))
    zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x00ffff00)
    zenbo.wheelLights.start_static(wheel_lights.Lights.SYNC_BOTH)
    zenbo.robot.set_expression(RobotFace.LAZY_ADV)
    zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x000000ff)
    zenbo.wheelLights.start_strobing(wheel_lights.Lights.SYNC_BOTH, wheel_lights.Speed.SPEED_DEFAULT)
    zenbo.media.stop_record_audio()
    print(f"record_audio_file: {record_audio_file}")
    if record_audio_file is not None:
        file_path, file_name = os.path.split(record_audio_file)
        print(os.getcwd()) 
        zenbo.media.file_transmission(f'{file_name}')
        # Convert aac to mp3
        aac_audio = AudioSegment.from_file(f"{file_name}", format="aac")
        aac_audio.export(f"{file_name[:-4]}.mp3", format="mp3")
        # Read the audio file and transcribe it, + generate a response.
        with open(f'{file_name[:-4]}.mp3', "rb") as f:
            response = requests.post(process_audio_url, files={"file": f, "conversation": str(conversation)})
        text_response = response.json()['llama_response'][-1]['content']
        transcription_response = response.json()['transcription']
        conversation.append({'user': transcription_response, 'zenbo': text_response})
        zenbo.robot.set_expression(RobotFace.PREVIOUS, text_response)
        time.sleep(int(1))
    time.sleep(0.5)
   

zenbo.robot.set_expression(RobotFace.DEFAULT)
time.sleep(int(0.5))
zenbo.on_result_callback = on_result_callback
zenbo.system.register_screen_touch_event(event_type=1, value=1)
time.sleep(int(1))

zenbo.robot.set_expression(RobotFace.INTERESTED_ADV)
zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x00ffff00)
zenbo.wheelLights.start_strobing(wheel_lights.Lights.SYNC_BOTH, wheel_lights.Speed.SPEED_DEFAULT)
zenbo.utility.track_face(False, False)
zenbo_speakLanguage = 2
zenbo.robot.set_expression(RobotFace.PREVIOUS, 'Hello, my name is Zenbo,  I am here to learn about how you are doing this week. Do you have any questions for me?', {'speed':zenbo_speakSpeed, 'pitch':zenbo_speakPitch, 'languageId':zenbo_speakLanguage} , sync = True)

for count in range(5):
    record_audio_and_respond()
    #zenbo.robot.set_expression(RobotFace.PREVIOUS, 'Ur boring, goodbye', {'speed':zenbo_speakSpeed, 'pitch':zenbo_speakPitch, 'languageId':zenbo_speakLanguage} , sync = True)
exit_function()

try:
  while True:
    time.sleep(int(10))
finally:
  exit_function()
