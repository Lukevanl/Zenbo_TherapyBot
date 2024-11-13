
from pyzenbo.modules import wheel_lights
import os
import threading
import pyzenbo
import pyzenbo.modules.zenbo_command as commands
import time
from pyzenbo.modules.dialog_system import RobotFace
record_audio_file = None
zenbo = pyzenbo.connect('')
def exit_function():
  zenbo.system.unregister_screen_touch_event(event_type=1, value=1)
  zenbo.robot.set_expression(RobotFace.DEFAULT)
  zenbo.release()
  time.sleep(1)
def on_result_callback(**kwargs):
  global record_audio_file
  if kwargs.get('cmd') == commands.SYSTEM_SCREEN_TOUCH_EVENT_REGISTER and kwargs.get('result').get('SCREEN_POINTER_COUNT') == 1 :
    def job():
      global zenbo_speakSpeed, zenbo_speakPitch, record_audio_file
      zenbo.media.record_audio(duration = 10, sync = False)
      time.sleep(int(1))
      zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x00ffff00, sync=False)
      zenbo.wheelLights.start_static(wheel_lights.Lights.SYNC_BOTH, sync=False)
      zenbo.robot.set_expression(RobotFace.SHY_ADV, sync=False)
      time.sleep(10)
      zenbo.media.stop_record_audio()
      zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x000000ff)
      zenbo.wheelLights.start_strobing(wheel_lights.Lights.SYNC_BOTH, wheel_lights.Speed.SPEED_DEFAULT)
      time.sleep(int(1))
      if record_audio_file is not None:
        filePath, fileName = os.path.split(record_audio_file)
        zenbo.media.play_media(filePath, fileName, sync = True)
        time.sleep(int(1))
    t = threading.Thread(target=job)
    t.start()
  if kwargs.get('cmd') == commands.MEDIA_RECORD_AUDIO or (kwargs.get('cmd') == commands.MEDIA_STOP_RECORD_AUDIO and '.aac' in kwargs.get('result').get('file')):
    record_audio_file = kwargs.get('result').get('file')
zenbo.robot.set_expression(RobotFace.DEFAULT)
time.sleep(int(0.5))
zenbo.on_result_callback = on_result_callback
zenbo.system.register_screen_touch_event(event_type=1, value=1)
time.sleep(int(1))

zenbo.robot.set_expression(RobotFace.INTERESTED_ADV)
zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x000000ff)
zenbo.wheelLights.start_strobing(wheel_lights.Lights.SYNC_BOTH, wheel_lights.Speed.SPEED_DEFAULT)
try:
  while True:
    time.sleep(int(10))
finally:
  exit_function()
