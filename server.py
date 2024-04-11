# -*- coding: utf-8 -*-
# Import necessary libraries
from flask import Flask, request
from waitress import serve
import services
import os
import logging
from dotenv import load_dotenv
import queue
import threading

# Load environment variables from .env file
load_dotenv()

# Set up logging with INFO level
logging.basicConfig(level=logging.INFO)

# Get the application token from environment variables
app_token = os.getenv("APP_TOKEN")

# If the application token is not set, log an error and exit
if app_token is None:
    logging.error("APP_TOKEN environment variable not set.")
    exit(1)

# Create a Flask application
app = Flask(__name__)

# Set the debug mode of the application based on the FLASK_DEBUG environment variable
app.config["DEBUG"] = os.getenv("FLASK_DEBUG")

# Define the index route
@app.route("/")
def index():
    # Return a simple message
    return "AIySha from roboMUA!"

# Define the welcome route
@app.route("/welcome", methods=["GET"])
def welcome():
    # Return a welcome message
    return "Hello there! My name is AIySha - your personal digital beauty advisor from roboMUA!"

# Define the webhook route for GET requests
@app.route("/webhook", methods=["GET"])
def verify_token():
    # Try to verify the token
    try:
        # Get the token and challenge from the request parameters
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        # If the token is correct and the challenge is not None, return the challenge
        if token == app_token and challenge != None:
            return challenge
        # If the token is incorrect, return an error message
        else:
            return "incorrect token.", 403
    # If an exception occurs, log the error and return an error message
    except Exception as e:
        logging.error("Error verifying token: {}".format(e))
        return "Error verifying token: {}".format(e), 500

# Create a queue to store the requests
request_queue = queue.Queue()

# Define a function to process the requests
def process_requests():
    # Process the requests indefinitely
    while True:
        # Get a request from the queue
        body = request_queue.get()

        # Try to process the request
        try:
            # Get the entry, changes, and value from the request body
            entry = body["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]

            # If the value contains statuses, skip this request
            if "statuses" in value:
                continue
            # If the value contains messages and contacts, process this request
            elif "messages" in value and "contacts" in value:
                # Get the number ID, message, number, message ID, contacts, and name from the value
                numberId = value["metadata"]["phone_number_id"]
                message = value["messages"][0]
                number = message["from"]
                messageId = message["id"]
                contacts = value["contacts"][0]
                name = contacts["profile"]["name"]
                                
                # Get the text from the message
                text = services.get_whatsapp_message(message)
                
                # Manage the chatbot with the text, number, message ID, name, and number ID
                services.manage_chatbot(text, number, messageId, name, numberId)
        # If an exception occurs, log the error
        except Exception as e:
            logging.error("Error processing message: {}".format(e))

        # Mark the request as done
        request_queue.task_done()

# Start a daemon thread to process the requests
threading.Thread(target=process_requests, daemon=True).start()

# Define the webhook route for POST requests
@app.route("/webhook", methods=["POST"])
def receive_messages():
    # Put the request data into the queue
    request_queue.put(request.get_json())
    # Return a success message
    return "Request received!", 200

# If this script is the main script
if __name__ == "__main__":
    # If the Flask environment is development, run the application
    if os.getenv("FLASK_ENV") == "development":
        app.run()
    # If the Flask environment is not development, serve the application
    else:
        serve(app)

