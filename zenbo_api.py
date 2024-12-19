from fastapi import FastAPI, UploadFile, File, Body, Form

from transformers import pipeline
import whisper
import torch
import os
import uvicorn
import time
from ngrok import ngrok
from transformers import pipeline
import librosa
import glob

ngrok.set_auth_token("2pZ5ADFOv6X3P2JYBN47uwSDo7U_51AxvVBAbgnZzC3erMrmB")

print(f"GPU Available: {torch.cuda.is_available()}")
print(f"GPU Device Count: {torch.cuda.device_count()}")
print(f"List of available GPU names: {[torch.cuda.get_device_name(x) for x in range(torch.cuda.device_count())]}")

app = FastAPI()
port = 8000

device = torch.device("cuda:1" if torch.cuda.is_available() else "cpu")
# Load models once during startup
print("Loading Whisper model...")
whisper_model = whisper.load_model("turbo", device=device)

print("Loading Llama 3.2 model...")
llama_pipeline = pipeline(
    "text-generation",
    model="meta-llama/Llama-3.2-3B-Instruct",
    torch_dtype=torch.bfloat16,
    device=device,
    #device_map="auto"
)
print("Loading GoEmotions model...")
classifier = pipeline(task="text-classification", model="SamLowe/roberta-base-go_emotions", top_k=None, device=device)

classifier_audio = pipeline("audio-classification", model="superb/hubert-large-superb-er", device=device)

print("Models loaded successfully.")

# Functions

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribes the given audio file using Whisper.
    """
    print(f"Transcribing audio file: {audio_path}")
    start_time = time.time()
    transcription_result = whisper_model.transcribe(audio_path)
    print(f"Transcription Time: {time.time() - start_time}")
    print(f"Transcription: {transcription_result['text']}")
    return transcription_result["text"]

def generate_response_llama(user_input: str, conversation: str = "") -> str:
    """
    Generates a response using Llama 3.2 based on user input text.
    """
    start_time = time.time()
    #instruction_prompt = "Get the user to elaborate on their feelings. Stay neutral and empathetic, never label the user's feelings. But you can ask on a scale of 1-10 how strongly they felt a certain emotion. Don't jump to conclusions of how something went or how they should feel, try to be more receiving and let them lead the conversation. You can ask how certain situations made them feel or what's going on in their mind. You can ask what problems they ran into. If the user presents a problem, try to help them figure out why they are feeling this way and how they could handle these situations better. Do not say I understand. Answer in 1 sentence. Always ask a question back."
    instruction_prompt = """Engage the user in a reflective conversation about their week. Stay empathetic, neutral, and non-judgmental. Use open-ended questions to encourage elaboration, but never suggest or assume specific feelings. Let the user lead the conversation by following their cues and expanding on what they share.

Ask about situations or events they experienced and how these made them feel. If the user describes a problem, help them explore why they feel this way and brainstorm approaches they might try. Avoid labeling or categorizing their feelings unless they have stated them clearly. Encourage self-expression by prompting gently but avoid giving options for what they might feel. After a user has stated they felt an emotion you may ask them how strongly they felt this emotion on a scale of 1-10.

When responding, be very concise and limit yourself to preferably one, but max two sentences. You may reflect on what they share to show attentiveness but avoid saying 'I understand.' Balance questions with short reflective statements to maintain a natural flow. Only give your (Zenbo's) reply as a string. """
    messages = [
        {"role": "system", "content": instruction_prompt},
        {"role": "user", "content": f"Conversation up until now: {conversation} \n\n Latest response by user: {user_input} \n\n Generate a fitting response to the user based on the conversation, keep it brief."}
    ]
    response = llama_pipeline(messages, max_new_tokens=75)
    print(f"Llama Response: {response}")
    print(f"Llama Time: {time.time() - start_time}")
    return response[0]["generated_text"]

def process_audio_and_generate_response(audio_path: str, conversation: str = "") -> dict:
    """
    Transcribes the audio file and generates a response using Llama 3.2.
    """
    transcription_text = transcribe_audio(audio_path)
    print(f"conversation: {conversation}")
    llama_response = generate_response_llama(transcription_text, conversation)
    text_emotions = detect_emotion_text(transcription_text)
    audio_emotions = detect_emotion_audio(audio_path)
    # Remove files
    files = glob.glob('./audio/*')
    for f in files:
        print(f)
        os.remove(f)
    return {
        "transcription": transcription_text,
        "llama_response": llama_response,
        "text_emotions": text_emotions,
        "audio_emotions": audio_emotions
    }

def detect_emotion_text(user_input: str) -> str:
    """
    Detects the emotion in the given user input text.
    """
    start_time = time.time()
    model_outputs = classifier([user_input])
    print(f"Emotion Detection Time: {time.time() - start_time}")
    print(model_outputs)
    return model_outputs

def detect_emotion_audio(file_path):
    y, sr = librosa.load(file_path)
    labels = classifier_audio(y, top_k=5)
    return labels

# API Endpoints

@app.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    """
    API endpoint for transcribing audio using Whisper.
    """
    # Save the uploaded audio file in the current directory
    os.makedirs("audio", exist_ok=True)
    audio_path = f"audio/{file.filename}"
    with open(f"audio/{file.filename}", "wb") as audio_file:
        audio_file.write(await file.read())
    transcription_text = transcribe_audio(audio_path)
    return {"transcription": transcription_text}

@app.post("/generate_response")
async def generate_response_endpoint(user_input: str):
    """
    API endpoint for generating a response using Llama 3.2.
    """
    llama_response = generate_response_llama(user_input)
    return {"llama_response": llama_response}

@app.post("/process_audio")
async def process_audio_endpoint(file: UploadFile = File(...), conversation: str = Form(...)):
    """
    API endpoint for processing audio (transcription + Llama 3.2 response).
    """
    print(f"conversation 2: {conversation}")
    audio_path = 'audio/' + file.filename
    with open(audio_path, "wb") as audio_file:
        audio_file.write(await file.read())
    result = process_audio_and_generate_response(audio_path, conversation)
    return result

@app.post("/detect_emotion_text")
async def emotion_detection_text(user_input: str = Body (...)):
    emotions = detect_emotion_text(user_input)
    return {"emotions": emotions}

@app.post("detect_emotion_audio")
async def emotion_detection_audio(file: UploadFile = File(...)):
    emotions = detect_emotions_audio(file)
    return {"emotions": emotions}


if __name__ == "__main__":
    public_url = ngrok.forward(port, domain="deep-generally-shrew.ngrok-free.app")
    print(f"Public URL: {public_url.url()}")
    uvicorn.run("zenbo_api:app", host="0.0.0.0", port=port, reload=False)
