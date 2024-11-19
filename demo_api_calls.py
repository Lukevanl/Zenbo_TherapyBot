
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
ip = "172.20.10.12"
transcribe_url = f"http://{ip}:8000/transcribe"
response_url = f"http://{ip}:8000/generate_response"
process_audio_url = f"http://{ip}:8000/process_audio"
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
  if kwargs.get('cmd') == commands.SYSTEM_SCREEN_TOUCH_EVENT_REGISTER and kwargs.get('result').get('SCREEN_POINTER_COUNT') == 1 :
    def job():
      global record_audio_file
      zenbo.media.record_audio(duration = 6, sync = False)
      time.sleep(int(5))
      zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x00ffff00)
      zenbo.wheelLights.start_static(wheel_lights.Lights.SYNC_BOTH)
      zenbo.robot.set_expression(RobotFace.LAZY_ADV)
      zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x000000ff)
      zenbo.wheelLights.start_strobing(wheel_lights.Lights.SYNC_BOTH, wheel_lights.Speed.SPEED_DEFAULT)
      zenbo.media.stop_record_audio()

      time.sleep(int(1))
      print(record_audio_file)
    #   if record_audio_file is not None:
    #     with open(record_audio_file, "rb") as f:
    #         response = requests.post(process_audio_url, files={"file": f})
    #     zenbo.robot.set_expression(RobotFace.PREVIOUS, response, {'speed':zenbo_speakSpeed, 'pitch':zenbo_speakPitch, 'languageId':zenbo_speakLanguage} , sync = True)
    #     time.sleep(int(1))
    t = threading.Thread(target=job)
    t.start()
  if kwargs.get('cmd') == commands.MEDIA_RECORD_AUDIO or (kwargs.get('cmd') == commands.MEDIA_STOP_RECORD_AUDIO and '.aac' in kwargs.get('result').get('file')):
    record_audio_file = kwargs.get('result').get('file')
    print(f"record_audio_file: {record_audio_file}")
    if record_audio_file is not None and kwargs.get('cmd') == commands.MEDIA_STOP_RECORD_AUDIO:
        #print(f"Directory: {os.listdir('/storage/')}")
        file_path, file_name = os.path.split(record_audio_file)
        #print('play_media', zenbo.media.play_media(file_path, file_name))
        print(os.getcwd()) 
        zenbo.media.file_transmission(f'{file_name}')
        aac_audio = AudioSegment.from_file(f"{file_name}", format="aac")
        aac_audio.export(f"{file_name[:-4]}.mp3", format="mp3")
        # file_transmission
        with open(f'{file_name}', "rb") as f:
            response = requests.post(process_audio_url, files={"file": f})
        text_response = response.json()['llama_response'][-1]['content']
        #zenbo.robot.set_expression(RobotFace.PREVIOUS, response, {'speed':zenbo_speakSpeed, 'pitch':zenbo_speakPitch, 'languageId':zenbo_speakLanguage} , sync = True)
        zenbo.robot.set_expression(RobotFace.PREVIOUS, text_response)
        time.sleep(int(1))
zenbo.robot.set_expression(RobotFace.DEFAULT)
time.sleep(int(0.5))
zenbo.on_result_callback = on_result_callback
zenbo.system.register_screen_touch_event(event_type=1, value=1)
time.sleep(int(1))

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
