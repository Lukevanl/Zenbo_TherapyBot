from decimal import *
from pydub import AudioSegment
import os
import glob
import sys
# Append cwd
sys.path.append(os.getcwd())
from pyzenbo.modules import wheel_lights
import threading
import time
import requests
from pyzenbo.modules.dialog_system import RobotFace
import pyzenbo
import pyzenbo.modules.zenbo_command as commands

emotions_mapping = {"sad": ["disappointment", "sadness", "embarrassment", "fear", "nervousness", "remorse", "grief"],
    "hap": ["approval", "optimism", "admiration", "joy", "amusement", "excitement", "love", "gratitude", "pride"],
    "neu": ["neutral", "realization", "confusion", "desire", "caring", "relief", "curiosity", "surprise"], 
    "ang": ["annoyance", "disapproval", "disgust", "anger"]}

# Zenbo IP
host = '172.20.10.2'
# ngrok URL from the server
url = "https://deep-generally-shrew.ngrok-free.app"

# API Endpoints (can be found in the line above each API endpoint in zenbo_api.py)
transcribe_url = url + "/transcribe"
response_url = url + "/generate_response"
process_audio_url = url + "/process_audio"
emotion_text_url = url + "/detect_emotion_text"
emotion_audio_url = url + "/detect_emotion_audio"


zenbo_speakSpeed = 100
zenbo_speakPitch = 100

# Has the robot started the introduction yet?
robotStart = False
screenNotPressed = True
finishedProcessing = False
# Rounds of conversation
roundsConvo = 6 
conversation_round = 0
# Connect to Zenbo
zenbo = pyzenbo.connect(host)

# Keeps track of the audio recording file and the conversation up to that point
record_audio_file = None
image_file = None
conversation = []


emotion_expression_mapping_1 = {
	"disapproval"	    : RobotFace.CONFIDENT,
	"annoyance" 	    : RobotFace.CONFIDENT,
	"neutral" 		    : RobotFace.DEFAULT,
	"anger" 		    : RobotFace.SERIOUS,
	"disappointment"    : RobotFace.CONFIDENT,
	"approval" 		    : RobotFace.ACTIVE,
	"realization" 	    : RobotFace.INTERESTED,
	"confusion" 		: RobotFace.DEFAULT, 
	"disgust" 		    : RobotFace.SERIOUS,
	"sadness" 		    : RobotFace.INNOCENT,
	"caring" 			: RobotFace.DEFAULT,
	"optimism" 		    : RobotFace.HAPPY,
	"gratitude" 		: RobotFace.ACTIVE,
	"joy" 			    : RobotFace.HAPPY,
	"amusement" 		: RobotFace.HAPPY,
	"love" 			    : RobotFace.HAPPY,
	"curiosity" 		: RobotFace.INTERESTED,
	"admiration" 		: RobotFace.ACTIVE,
	"embarrassment" 	: RobotFace.CONFIDENT,
	"desire" 			: RobotFace.DEFAULT,
	"surprise" 		    : RobotFace.INTERESTED,
	"excitement" 		: RobotFace.HAPPY, 
	"remorse" 		    : RobotFace.DEFAULT,
	"fear" 			    : RobotFace.CONFIDENT, 
	"relief" 			: RobotFace.ACTIVE,
	"nervousness" 	    : RobotFace.CONFIDENT,
	"grief" 			: RobotFace.INNOCENT,
	"pride" 			: RobotFace.ACTIVE
}

emotion_expression_mapping_2 = {
	"disapproval"    : RobotFace.DEFAULT,
	"annoyance"     : RobotFace.DEFAULT,
	"neutral"         : RobotFace.DEFAULT,
	"anger"           : RobotFace.DEFAULT,
	"disappointment"    : RobotFace.DEFAULT,
	"approval"         : RobotFace.DEFAULT,
	"realization"      : RobotFace.DEFAULT,
	"confusion"        : RobotFace.DEFAULT, 
	"disgust"          : RobotFace.DEFAULT,
	"sadness"          : RobotFace.DEFAULT,
	"caring"           : RobotFace.DEFAULT,
	"optimism"         : RobotFace.DEFAULT,
	"gratitude"        : RobotFace.DEFAULT,
	"joy"              : RobotFace.DEFAULT,
	"amusement"        : RobotFace.DEFAULT,
	"love"             : RobotFace.DEFAULT,
	"curiosity"        : RobotFace.DEFAULT,
	"admiration"       : RobotFace.DEFAULT,
	"embarrassment"    : RobotFace.DEFAULT,
	"desire"           : RobotFace.DEFAULT,
	"surprise"         : RobotFace.DEFAULT,
	"excitement"       : RobotFace.DEFAULT, 
	"remorse"          : RobotFace.DEFAULT,
	"fear"             : RobotFace.DEFAULT, 
	"relief"           : RobotFace.DEFAULT,
	"nervousness"      : RobotFace.DEFAULT,
	"grief"            : RobotFace.DEFAULT,
	"pride"            : RobotFace.DEFAULT
}


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
   """""""""""""""""""""" CHOOSE MODEL 1 OR 2 """"""""""""""""""""""
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
# MODEL 1: EMOTION
# MODEL 2: NO EMOTION
model = 1
intro = False
opening_question = 'So, hows life going?'  

if model == 1:
  # model 1
  facial_expression_model_specific = RobotFace.ACTIVE
  emotion_expression_mapping = emotion_expression_mapping_1
else:
  # model 2
  facial_expression_model_specific = RobotFace.DEFAULT 
  emotion_expression_mapping = emotion_expression_mapping_2 

# Make sure the 'previous expression' starts with the one that suits the chosen model
PreviousExpression = facial_expression_model_specific


# Gets called when the program is exited
def exit_function():
  zenbo.system.unregister_screen_touch_event(event_type=1, value=1)
  zenbo.robot.set_expression(RobotFace.TIRED_ADV)
  zenbo.release()
  time.sleep(1)


def on_result_callback(**kwargs):
  global zenbo_speakSpeed, zenbo_speakPitch, record_audio_file, robotStart, finishedProcessing
  if kwargs.get('cmd') == commands.SYSTEM_SCREEN_TOUCH_EVENT_REGISTER and kwargs.get('result').get('SCREEN_POINTER_COUNT') == 1 :

    if robotStart == False:
       print('starting...')
       robotStart = True
       t = threading.Thread(target=start_signal)
       t.start()
    else:
      screenNotPressed=False
      print('stopping recording...')
      t = threading.Thread(target=stop_recording)
      t.start()

      
  # Gets called when a result is returned from Zenbo, this handles the audio recording.
  if kwargs.get('cmd') == commands.MEDIA_RECORD_AUDIO or (kwargs.get('cmd') == commands.MEDIA_STOP_RECORD_AUDIO and '.aac' in kwargs.get('result').get('file')):
    record_audio_file = kwargs.get('result').get('file')
  if kwargs.get('cmd') == commands.MEDIA_TAKE_PICTURE:
    global image_file
    image_file = kwargs.get('result').get('file')



# Records audio, sends it to the server for processing
def record_audio_and_respond():
    global finishedProcessing, PreviousExpression
    # Record audio, sync = False to allow for other commands to be executed while recording (e.g changing the emotion of Zenbo)
    zenbo.media.record_audio(duration = 100, sync = False)
    time.sleep(0.5)

    # Set the wheel lights to strobing to indicate that Zenbo is listening, also set the expression to interested
    zenbo.robot.set_expression(RobotFace.PREVIOUS, sync=False) 
    zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x000000ff)
    zenbo.wheelLights.start_comet(wheel_lights.Lights.SYNC_BOTH, direction = wheel_lights.Direction.DIRECTION_FORWARD, speed=wheel_lights.Speed.SPEED_DEFAULT)

    while not finishedProcessing:
       zenbo.robot.set_expression(PreviousExpression, sync=False)
       time.sleep(0.5)
  
    finishedProcessing=False


# Processes the recording and creates the appropriate response, also pick the fitting emotional expression
def process_recording():
    global conversation_round, roundsConvo, PreviousExpression
    # if we are at the final round of conversation
    if conversation_round == roundsConvo:
      time.sleep(1)
      zenbo.robot.set_expression(RobotFace.TIRED, 'Im sorry, I see that it is becoming late, I have to go. It was nice talking to you, hope you have a nice day!.', {'speed':zenbo_speakSpeed, 'pitch':zenbo_speakPitch} , sync = True)
      time.sleep(1)
      exit_function()
    print(f"record_audio_file: {record_audio_file}")
    # If the audio file is not None, send it to the server for processing
    if record_audio_file is not None:  
        file_path, file_name = os.path.split(record_audio_file)
        
        # Sends the audio file from zenbo to the server so it can be processed
        zenbo.media.file_transmission(f'{file_name}')
        # Convert aac to mp3
        aac_audio = AudioSegment.from_file(f"{file_name}", format="aac")
        aac_audio.export(f"{file_name[:-3]}mp3", format="mp3")
        # Read the audio file and transcribe it, + generate a response.
        if image_file is not None:  
          file_path, file_name = os.path.split(image_file)
          # Sends the audio file from zenbo to the server so it can be processed
          zenbo.media.file_transmission(f'{file_name}')
        with open(file_name, "rb") as f:
            process_response = requests.post(process_audio_url, files={"file": f}, data={"conversation": str(conversation)})


        # Get the responses from the API
        text_response = process_response.json()['llama_response'][-1]['content']
        transcription_response = process_response.json()['transcription']
        # get the emotion from the user's transcribed response
        emotions_text = process_response.json()["text_emotions"]
        emotions_audio = process_response.json()["audio_emotions"]
        # retrieve the strongest emotion detected (combined from text and audio)
        emotion_final = combine_emotion(emotions_text, emotions_audio)
        facial_expression = emotion_expression_mapping[emotion_final]
        PreviousExpression = facial_expression
        zenbo_speakLanguage = 2
        # Make Zenbo say the response to what the user said & choose the fitting emotion
        zenbo.robot.set_expression(facial_expression, text_response, {'speed':zenbo_speakSpeed, 'pitch':zenbo_speakPitch, 'languageId':zenbo_speakLanguage})
        # Keep track of the conversation
        conversation.append({'user': transcription_response, 'zenbo': text_response})
        time.sleep(int(0.5))
      
    time.sleep(0.5)
   


def combine_emotion(emotions_text, emotions_audio):
   # Flatten the emotions_text list
    emotions_text = emotions_text[0]  
    # Initialize a dictionary to store the combined scores
    combined_scores = {}
    # Iterate over the audio emotions
    for audio_emotion in emotions_audio:
        audio_label = audio_emotion["label"]
        audio_score = audio_emotion["score"]
        # Map the audio label to the corresponding text labels
        mapped_text_labels = emotions_mapping[audio_label]

        # Iterate over the mapped text labels
        for text_emotion in emotions_text:
            text_label = text_emotion["label"]
            text_score = text_emotion["score"]

            # If the text label matches one of the mapped labels, combine the scores
            if text_label in mapped_text_labels:
                if text_label not in combined_scores:
                    combined_scores[text_label] = 0

                # Combine scores (weighted sum)
                combined_scores[text_label] += audio_score * 0.25 + text_score

    # Normalize the combined scores to sum to 1
    total_score = sum(combined_scores.values())
    if total_score > 0:
        for label in combined_scores:
            combined_scores[label] /= total_score

    # Convert the combined scores dictionary to a sorted list of dictionaries
    combined_emotions = [
        {"label": label, "score": score}
        for label, score in sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)]
    
    # Find the max element by 'score'
    max_emotion = combined_emotions[0]['label']
    return max_emotion
         
  
# Zenbo introduces itself to the user
def introduce_self():
    global facial_expression_model_specific
    zenbo_speakLanguage = 2
    zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x000000ff)
    zenbo.wheelLights.start_static(wheel_lights.Lights.SYNC_BOTH)
    zenbo.robot.set_expression(facial_expression_model_specific, 'Hello! I’m Zenbo, a social robot here to have a friendly chat with you. This is a safe space, so feel free to share whatever you are comfortable with. I’m here to listen and respond, and there’s no right or wrong way to interact. We can talk about anything, your day, your feelings, your work, whatever you prefer. Let me show you how I work! I will ask you a question and then you can respond, when you are done talking you can touch the screen and I will respond. For the rest you might notice the lights stay on when I talk. Once I stop talking they will start spinning to show that you are being recorded. Let me demonstrate that for you now',{'speed':zenbo_speakSpeed, 'pitch':zenbo_speakPitch, 'languageId':zenbo_speakLanguage})
    zenbo.wheelLights.start_comet(wheel_lights.Lights.SYNC_BOTH, direction = wheel_lights.Direction.DIRECTION_FORWARD, speed=wheel_lights.Speed.SPEED_DEFAULT)
    time.sleep(5)
    zenbo.wheelLights.start_static(wheel_lights.Lights.SYNC_BOTH)
 

def stop_recording():
    global finishedProcessing
    # Stop recording audio, and set the wheel lights to static
    zenbo.media.stop_record_audio()
    zenbo.wheelLights.start_static(wheel_lights.Lights.SYNC_BOTH)
    zenbo.robot.set_expression(RobotFace.PREVIOUS) 
    process_recording()
    finishedProcessing = True



def start_signal():
  global model, conversation_round, opening_question
  zenbo.motion.move_body(0.15, 0, 0, speed_level = 2, sync = True)
  # Set the expression to interested and the wheel lights to static
  zenbo.motion.move_head(pitch_degree = 20, speed_level = 2, sync = True)
  zenbo.utility.track_face(False, False)
  time.sleep(0.5)
  zenbo.wheelLights.set_color(wheel_lights.Lights.SYNC_BOTH, 0xff, 0x000000ff)
  time.sleep(0.5)
  zenbo.wheelLights.start_static(wheel_lights.Lights.SYNC_BOTH)
  if intro:
     introduce_self()
  zenbo_speakLanguage = 2
  zenbo.robot.set_expression(RobotFace.PREVIOUS, opening_question, {'speed':zenbo_speakSpeed, 'pitch':zenbo_speakPitch, 'languageId':zenbo_speakLanguage} , sync = True)
  

  for count in range(roundsConvo):
      conversation_round += 1
      record_audio_and_respond()
                 
zenbo.robot.set_expression(RobotFace.ACTIVE) 
time.sleep(int(0.5))
zenbo.on_result_callback = on_result_callback
zenbo.system.register_screen_touch_event(event_type=1, value=1)
time.sleep(int(1))


try:
  while True:
    time.sleep(int(10))
finally:
  files = glob.glob('./*')
  for f in files:
      if f[-4:] in [".aac", ".mp3"]:
          os.remove(f)
  exit_function()
