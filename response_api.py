from fastapi import FastAPI, UploadFile, File
from transformers import pipeline
import whisper
import torch
import os
import uvicorn
import time

app = FastAPI()

# Load models once during startup
whisper_model = whisper.load_model("base.en")
llama_pipeline = pipeline(
    "text-generation",
    model="meta-llama/Llama-3.2-3B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

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

def generate_response_llama(user_input: str, conversation: str) -> str:
    """
    Generates a response using Llama 3.2 based on user input text.
    """
    start_time = time.time()
    instruction_prompt = "Get the user to elaborate on their feelings. Stay neutral and empathetic, don't put a label on their feelings. You can ask how certain situations made them feel or what's going on in their mind. You can ask what problems they ran into.  Do not say I understand. Answer in 1 sentence."
    messages = [
        {"role": "system", "content": instruction_prompt},
        {"role": "user", "content": f"Conversation up until now: {conversation} \n\n Latest response by user: {user_input} \n\n Generate a fitting response to the user based on the conversation, keep it brief."}
    ]
    response = llama_pipeline(messages, max_new_tokens=50)
    print(f"Llama Response: {response}")
    print(f"Llama Time: {time.time() - start_time}")
    return response[0]["generated_text"]

def process_audio_and_generate_response(audio_path: str, conversation: str = "") -> dict:
    """
    Transcribes the audio file and generates a response using Llama 3.2.
    """
    transcription_text = transcribe_audio(audio_path)
    llama_response = generate_response_llama(transcription_text, conversation)
    return {
        "transcription": transcription_text,
        "llama_response": llama_response
    }

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
async def process_audio_endpoint(file: UploadFile = File(...), conversation: str = ""):
    """
    API endpoint for processing audio (transcription + Llama 3.2 response).
    """
    audio_path = file.filename
    with open(audio_path, "wb") as audio_file:
        audio_file.write(await file.read())
    result = process_audio_and_generate_response(audio_path, conversation)
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
