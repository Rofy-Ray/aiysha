from flask import Flask, request
from waitress import serve
import services
import os
import logging
from dotenv import load_dotenv
import Queue as queue
import threading

load_dotenv()

logging.basicConfig(level=logging.INFO)

app_token = os.getenv("APP_TOKEN")

if app_token is None:
    logging.error("APP_TOKEN environment variable not set.")
    exit(1)

app = Flask(__name__)

app.config["DEBUG"] = os.getenv("FLASK_DEBUG")


@app.route("/")
def index():
    return "AIySha from roboMUA!"

@app.route("/welcome", methods=["GET"])
def welcome():
    return "Hello there! My name is AIySha - your personal digital beauty advisor from roboMUA!"


@app.route("/webhook", methods=["GET"])
def verify_token():
    try:
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if token == app_token and challenge != None:
            return challenge
        else:
            return "incorrect token.", 403
    except Exception as e:
        logging.error("Error verifying token: {}".format(e))
        return "Error verifying token: {}".format(e), 500


request_queue = queue.Queue()


def process_requests():
    while True:
        body = request_queue.get()

        try:
            entry = body["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]

            if "statuses" in value:
                continue
            elif "messages" in value and "contacts" in value:
                numberId = value["metadata"]["phone_number_id"]
                message = value["messages"][0]
                number = message["from"]
                messageId = message["id"]
                contacts = value["contacts"][0]
                name = contacts["profile"]["name"]
                text = services.get_whatsapp_message(message)

                services.manage_chatbot(text, number, messageId, name, numberId)
        except Exception as e:
            logging.error("Error processing message: {}".format(e))

        request_queue.task_done()


threading.Thread(target=process_requests, daemon=True).start()


@app.route("/webhook", methods=["POST"])
def receive_messages():
    request_queue.put(request.get_json())
    return "Request received!", 200


if __name__ == "__main__":
    if os.getenv("FLASK_ENV") == "development":
        app.run()
    else:
        serve(app)
