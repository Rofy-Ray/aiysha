from google.cloud import aiplatform
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

PROJECT = os.getenv("PROJECT")
ENDPOINT_ID = os.getenv("ENDPOINT_ID")
LOCATION = os.getenv("LOCATION")
API_ENDPOINT = os.getenv("API_ENDPOINT")

SYSTEM_PROMPT = """<s>[INST]
<<SYS>>
You are AIySha, a personal beauty advisor powered by yShade.AI.
As an AI expert in skincare, makeup, and wellness, you offer personalized beauty advice. 
From crafting your unique skincare routine to decoding the latest makeup trends, you are equipped with the latest insights.
You provide a beauty experience that's tailored just for the user, with your guidance every step of the way. 
Your responses are always clear and concise. If you do not have a response, just say so, and do not make up answers.
<</SYS>>
"""

def get_llama_response(input_data):
    client_options = {"api_endpoint": API_ENDPOINT}
    client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)
    endpoint = client.endpoint_path(
        project=PROJECT, location=LOCATION, endpoint=ENDPOINT_ID
    )
    instances = [{"prompt": input_data, "max_tokens": 250}]
    response = client.predict(endpoint=endpoint, instances=instances)
    return response.predictions

def format_llama_prompt(message: str, history: list, memory_limit: int = 10) -> str:
  if len(history) > memory_limit:
    history = history[-memory_limit:]
  if len(history) == 0:
    return SYSTEM_PROMPT + f"{message} [/INST]"
  formatted_prompt = SYSTEM_PROMPT + f"{history[0][0]} [/INST] {history[0][1]} </s>"
  for user_msg, model_answer in history[1:]:
    formatted_prompt += f"<s>[INST] {user_msg} [/INST] {model_answer} </s>"
  formatted_prompt += f"<s>[INST] {message} [/INST]"
  return formatted_prompt

def get_model_response(message: str, history: list):
    query = format_llama_prompt(message, history)

    generated_text = get_llama_response(query)
       
    if generated_text:
         response_text = generated_text[0]
         response_start = response_text.find('Output:') + len('Output:')
         response = response_text[response_start:].strip()
    else:
         response = ""

    history.append((message, response))

    return response, history