# -*- coding: utf-8 -*-
# Import necessary libraries
import requests
import json
import time
import os
import logging
import base64
import collections
import textwrap
from typing import Tuple, List, Dict, Optional, Any
from PIL import Image
from io import BytesIO
from tempfile import NamedTemporaryFile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import configparser
from dotenv import load_dotenv
from data import greetings, all_image_options, plus_color_options
from llama import get_model_response

# Load environment variables from .env file
load_dotenv()

# Set up logging with INFO level
logging.basicConfig(level=logging.INFO)

# Open and load JSON data from options.json file
with open("options.json") as f:
    feats = json.load(f)

# Read configuration from config.ini file
config = configparser.ConfigParser()
config.read("config.ini")

# Get URLs for different services from the configuration
hair_color_try_on_edge = config["url"]["hair_color_try_on_edge"]
lip_stick_try_on_edge = config["url"]["lip_stick_try_on_edge"]
lip_liner_try_on_edge = config["url"]["lip_liner_try_on_edge"]
hair_style_try_on_edge = config["url"]["hair_style_try_on_edge"]
foundation_recs_edge = config["url"]["foundation_recs_edge"]
concealer_recs_edge = config["url"]["concealer_recs_edge"]
setting_powder_recs_edge = config["url"]["setting_powder_recs_edge"]
contour_recs_edge = config["url"]["contour_recs_edge"]
bronzer_recs_edge = config["url"]["bronzer_recs_edge"]
shape_wear_recs_edge = config["url"]["shape_wear_recs_edge"]
nude_shoes_recs_edge = config["url"]["nude_shoes_recs_edge"]


def get_whatsapp_message(message: Dict) -> str:
    """
    This function processes a WhatsApp message and extracts the text based on the type of the message.

    Parameters:
    message (dict): A dictionary containing the WhatsApp message data. The 'type' key in the dictionary 
                    indicates the type of the message.

    Returns:
    str: The extracted text from the WhatsApp message. If the message type is not recognized or processed, 
         it returns a default text.
    """
    # Check if the 'type' key is in the message
    if "type" not in message:
        text = "message not recognized."
        return text

    # Extract the message type
    typeMessage = message["type"]

    # Process the message based on its type
    if typeMessage == "text":
        # For 'text' type, the text is in the 'body' key of the 'text' dictionary
        text = message["text"]["body"]
    elif typeMessage == "image":
        # For 'image' type, the text is the 'id' of the image
        text = message["image"]["id"]
    elif typeMessage == "button":
        # For 'button' type, the text is the 'text' of the button
        text = message["button"]["text"]
    elif typeMessage == "interactive" and message["interactive"]["type"] == "list_reply":
        # For 'interactive' type with a 'list_reply', the text is the 'title' of the 'list_reply'
        text = message["interactive"]["list_reply"]["title"]
    elif typeMessage == "interactive" and message["interactive"]["type"] == "button_reply":
        # For 'interactive' type with a 'button_reply', the text is the 'title' of the 'button_reply'
        text = message["interactive"]["button_reply"]["title"]
    else:
        # If the message type is not recognized or processed, return a default text
        text = "message not processed."

    return text


def send_whatsapp_message(data: str) -> Tuple[str, int]:
    """
    This function sends a WhatsApp message using the provided data.

    Parameters:
    data (str): A string containing the WhatsApp message data.

    Returns:
    Tuple[str, int]: A tuple containing a message about the status of the operation and an HTTP status code.
    """
    try:
        # Get the WhatsApp token and environment variables
        whatsapp_token = os.getenv("WHATSAPP_TOKEN")
        flask_env = os.getenv("FLASK_ENV")

        # Determine the WhatsApp URL based on the environment
        whatsapp_url = (
            os.getenv("WHATSAPP_URL_DEV")
            if flask_env == "development"
            else os.getenv("WHATSAPP_URL_PROD")
        )

        # Define the headers for the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + whatsapp_token,
        }

        # Send the POST request to the WhatsApp URL
        response = requests.post(whatsapp_url, headers=headers, data=data)

        # If the request was unsuccessful, raise an exception
        response.raise_for_status()

        # Wait for 5 seconds to ensure the message is sent
        time.sleep(5)

        # Return a success message and status code
        return "message sent!", 200
    except requests.HTTPError as http_err:
        # If an HTTP error occurred, return an error message and the status code
        return f"HTTP error occurred: {http_err}", response.status_code
    except Exception as err:
        # If any other error occurred, return an error message and a 403 status code
        return f"Other error occurred: {err}", 403


def text_message(number: str, text: str) -> str:
    """
    This function creates a JSON string for a WhatsApp text message.

    Parameters:
    number (str): The phone number of the recipient.
    text (str): The text of the message.

    Returns:
    str: A JSON string representing the WhatsApp text message.
    """
    # Create a dictionary with the WhatsApp message data
    data_dict = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "text",
        "text": {"body": text},
    }

    # Convert the dictionary to a JSON string
    data = json.dumps(data_dict)

    return data


def button_reply_message(number: str, options: List[str], body: str, footer: str, scenario: str, messageId: str) -> str:
    """
    This function creates a JSON string for a WhatsApp button reply message.

    Parameters:
    number (str): The phone number of the recipient.
    options (List[str]): A list of options for the button reply.
    body (str): The body text of the message.
    footer (str): The footer text of the message.
    scenario (str): The scenario for the button reply.
    messageId (str): The message ID.

    Returns:
    str: A JSON string representing the WhatsApp button reply message.
    """
    # Initialize an empty list for the buttons
    buttons = []

    # Create a button for each option
    for i, option in enumerate(options):
        buttons.append(
            {
                "type": "reply",
                "reply": {"id": scenario + "_btn_" + str(i + 1), "title": option},
            }
        )

    # Create a dictionary with the WhatsApp message data
    data_dict = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "footer": {"text": footer},
            "action": {"buttons": buttons},
        },
    }

    # Convert the dictionary to a JSON string
    data = json.dumps(data_dict)

    return data


def list_reply_message(number: str, options: List[str], body: str, footer: str, scenario: str, messageId: str) -> str:
    """
    This function creates a JSON string for a WhatsApp list reply message.

    Parameters:
    number (str): The phone number of the recipient.
    options (List[str]): A list of options for the list reply.
    body (str): The body text of the message.
    footer (str): The footer text of the message.
    scenario (str): The scenario for the list reply.
    messageId (str): The message ID.

    Returns:
    str: A JSON string representing the WhatsApp list reply message.
    """
    # Initialize an empty list for the rows
    rows = []

    # Create a row for each option
    for i, option in enumerate(options):
        rows.append(
            {"id": scenario + "_row_" + str(i + 1), "title": option, "description": ""}
        )

    # Create a dictionary with the WhatsApp message data
    data_dict = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "footer": {"text": footer},
            "action": {
                "button": "See Options",
                "sections": [{"title": "Sections", "rows": rows}],
            },
        },
    }

    # Convert the dictionary to a JSON string
    data = json.dumps(data_dict)

    return data


def document_message(number: str, docId: str, caption: str, filename: str) -> str:
    """
    This function creates a JSON string for a WhatsApp document message.

    Parameters:
    number (str): The phone number of the recipient.
    docId (str): The ID of the document.
    caption (str): The caption of the document.
    filename (str): The filename of the document.

    Returns:
    str: A JSON string representing the WhatsApp document message.
    """
    # Create a dictionary with the WhatsApp message data
    data_dict = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "document",
        "document": {"id": docId, "caption": caption, "filename": filename},
    }

    # Convert the dictionary to a JSON string
    data = json.dumps(data_dict)

    return data


def image_message(number: str, image_id: str) -> str:
    """
    This function creates a JSON string for a WhatsApp image message.

    Parameters:
    number (str): The phone number of the recipient.
    image_id (str): The ID of the image.

    Returns:
    str: A JSON string representing the WhatsApp image message.
    """
    # Create a dictionary with the WhatsApp message data
    data_dict = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "image",
        "image": {"id": image_id},
    }

    # Convert the dictionary to a JSON string
    data = json.dumps(data_dict)

    return data


def sticker_message(number: str, sticker_id: str) -> str:
    """
    This function creates a JSON string for a WhatsApp sticker message.

    Parameters:
    number (str): The phone number of the recipient.
    sticker_id (str): The ID of the sticker.

    Returns:
    str: A JSON string representing the WhatsApp sticker message.
    """
    # Create a dictionary with the WhatsApp message data
    data_dict = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "sticker",
        "sticker": {"id": sticker_id},
    }

    # Convert the dictionary to a JSON string
    data = json.dumps(data_dict)

    return data


def get_media_id(media_name: str, media_type: str) -> Optional[str]:
    """
    This function retrieves the ID of a media file based on its name and type.

    Parameters:
    media_name (str): The name of the media file.
    media_type (str): The type of the media file. It can be 'sticker', 'image', 'video', or 'audio'.

    Returns:
    Optional[str]: The ID of the media file if it exists, None otherwise.
    """
    # Initialize the media ID as an empty string
    media_id = ""

    # Retrieve the media ID based on the media type
    if media_type == "sticker":
        media_id = STICKER_ID.get(media_name, None)
    elif media_type == "image":
        media_id = IMAGE_ID.get(media_name, None)
    elif media_type == "video":
        media_id = VIDEO_ID.get(media_name, None)
    elif media_type == "audio":
        media_id = AUDIO_ID.get(media_name, None)

    return media_id


def reply_reaction_message(number: str, messageId: str, emoji: str) -> str:
    """
    This function creates a JSON string for a WhatsApp reply reaction message.

    Parameters:
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message to which the reaction is being sent.
    emoji (str): The emoji used for the reaction.

    Returns:
    str: A JSON string representing the WhatsApp reply reaction message.
    """
    # Create a dictionary with the WhatsApp message data
    data_dict = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "reaction",
        "reaction": {"message_id": messageId, "emoji": emoji},
    }

    # Convert the dictionary to a JSON string
    data = json.dumps(data_dict)

    return data


def reply_text_message(number: str, messageId: str, text: str) -> str:
    """
    This function creates a JSON string for a WhatsApp reply text message.

    Parameters:
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message to which the reply is being sent.
    text (str): The text of the reply.

    Returns:
    str: A JSON string representing the WhatsApp reply text message.
    """
    # Create a dictionary with the WhatsApp message data
    data_dict = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "context": {"message_id": messageId},
        "type": "text",
        "text": {"body": text},
    }

    # Convert the dictionary to a JSON string
    data = json.dumps(data_dict)

    return data


def mark_read_message(messageId: str) -> str:
    """
    This function creates a JSON string for marking a WhatsApp message as read.

    Parameters:
    messageId (str): The ID of the message to be marked as read.

    Returns:
    str: A JSON string representing the WhatsApp read status update.
    """
    # Create a dictionary with the WhatsApp message data
    data_dict = {
        "messaging_product": "whatsapp", 
        "status": "read", 
        "message_id": messageId
    }

    # Convert the dictionary to a JSON string
    data = json.dumps(data_dict)

    return data


def ask_for_selfie(number: str) -> str:
    """
    This function creates a text message asking the user to send a selfie.

    Parameters:
    number (str): The phone number of the recipient.

    Returns:
    str: A text message asking the user to send a selfie.

    Raises:
    Exception: If an error occurs while creating the text message.
    """
    try:
        # Define the text of the message
        send_text = text_message(
            number,
            textwrap.dedent(
                """
                    Great! Now, I need to see your beautiful face in all its glory. 
                    For ```foundation, skin tint, concealer, setting powder, contour, bronzer:``` `Send SELFIE` 
                    For ```hair style or hair color:``` `Send SELFIE with full hair visible`
                    For ```shapewear or nude shoes:``` `Snap Skin Patch` 
                    Let’s make sure you find the right fit!
                    But make sure you’re not wearing any makeup or glasses. I want to see the real you, not the filtered version.
                """
            ),
        )
        return send_text
    except Exception as e:
        # Log the error and re-raise it
        logging.error(f"Error occurred while asking for selfie: {e}")
        raise


def pause_text(number: str) -> Tuple[str, int]:
    """
    This function creates a text message asking the user to wait while an image or photo is being processed to generate recommendations or show results.

    Parameters:
    number (str): The phone number of the recipient.

    Returns:
    Tuple[str, int]: A text message asking the user to wait and a status code.

    Raises:
    Exception: If an error occurs while creating the text message.
    """
    try:
        # Define the text of the message
        send_text = text_message(
            number,
            "Hang tight! I’m whipping up some digital wizardry as we speak. It’s like a techy cauldron bubbling with bytes and bits – your wish is my command line. 🧙‍♂️💻✨",
        )
        return send_text, 200
    except Exception as e:
        # Log the error and re-raise it
        logging.error(f"Error occurred while asking user to hold on: {e}")
        raise


def follow_up(number: str, messageId: str) -> str:
    """
    This function creates a button reply message for a follow-up question after the user has received recommendations or the result of a virtual try-on.

    Parameters:
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message to which the reply is being sent.

    Returns:
    str: A JSON string representing the WhatsApp button reply message.
    """
    # Define the body, footer, and options of the message
    body = "Your radiance was truly captivating! As the curtain rises on the next chapter of your style journey, can I assist in crafting your upcoming show-stopping look? 🌟🎭✨"
    footer = "AIySha by roboMUA"
    options = ["✅ Yes, please.", "❌ No, thanks."]

    # Create a button reply message
    reply_button_data = button_reply_message(
        number, options, body, footer, "scenario4", messageId
    )

    return reply_button_data


def remove_emoji_and_strip(input_string: str) -> str:
    """
    This function removes the first two characters (usually an emoji) from a string and then removes any leading or trailing whitespace if the string has an emoji.

    Parameters:
    input_string (str): The input string from which the first two characters and any leading or trailing whitespace should be removed.

    Returns:
    str: The input string with the first two characters and any leading or trailing whitespace removed.
    """
    # Remove the first two characters from the string and then strip any leading or trailing whitespace
    return input_string[2:].strip()


def download_media(media_id: str, number_id: str, retries: int = 3) -> Optional[str]:
    """
    This function downloads a media file from WhatsApp.

    Parameters:
    media_id (str): The ID of the media file.
    number_id (str): The ID of the phone number.
    retries (int, optional): The number of times to retry the download if it fails. Defaults to 3.

    Returns:
    Optional[str]: The path of the downloaded media file if the download is successful, None otherwise.

    Raises:
    requests.exceptions.RequestException: If a request to the WhatsApp API fails.
    Exception: If any other error occurs.
    """
    # Get the WhatsApp token and media URL from the environment variables
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    whatsapp_media_url = os.getenv("WHATSAPP_MEDIA_URL")

    # Construct the media URL
    media_url = "{}/{}?phone_number_id={}".format(
        whatsapp_media_url, media_id, number_id
    )

    # Define the headers for the request
    headers = {"Authorization": "Bearer " + whatsapp_token}

    # Try to download the media file
    for i in range(retries):
        try:
            # Send a GET request to the media URL
            response = requests.get(media_url, headers=headers)

            # If the request was unsuccessful, raise an exception
            response.raise_for_status()

            # Get the media data from the response
            media_data = response.json()

            # Get the URL of the media file
            media_url = media_data.get("url")

            # If the media URL is not None, download the media file
            if media_url:
                # Send a GET request to the media URL
                response = requests.get(media_url, headers=headers)

                # If the request was unsuccessful, raise an exception
                response.raise_for_status()

                # Open the media file as an image
                image = Image.open(BytesIO(response.content))

                # Save the image to a temporary file
                downloaded_temp_file = NamedTemporaryFile(delete=False, suffix=".jpeg")
                image.save(downloaded_temp_file.name, format="JPEG")

                # Return the path of the temporary file
                return downloaded_temp_file.name
        except requests.exceptions.RequestException as e:
            # Log the error
            logging.error(f"Request failed: {e}")

            # If this was the last retry, re-raise the exception
            if i == retries - 1:
                raise
        except Exception as e:
            # Log the error and re-raise the exception
            logging.error(e)
            raise


def fetch_vto_image(url: str, color: str, temp_file_path: str, retries: int = 3) -> Optional[str]:
    """
    This function fetches a virtual try-on (VTO) image from a given URL.

    Parameters:
    url (str): The URL from which to fetch the VTO image.
    color (str): The color to be used for the VTO.
    temp_file_path (str): The path of the temporary file to be used for storing the VTO image.
    retries (int, optional): The number of times to retry the fetch if it fails. Defaults to 3.

    Returns:
    Optional[str]: The path of the fetched VTO image if the fetch is successful, None otherwise.

    Raises:
    requests.exceptions.RequestException: If a request to the URL fails.
    Exception: If any other error occurs.
    """
    # Try to fetch the VTO image
    for i in range(retries):
        try:
            # Open the temporary file
            with open(temp_file_path, "rb") as temp_file:
                # Send a POST request to the URL with the color and the temporary file
                response = requests.post(
                    url, data={"color": color}, files={"file": temp_file}
                )

            # If the request was unsuccessful, raise an exception
            response.raise_for_status()

            # Decode the base64 image data from the response
            image_data = base64.b64decode(response.json().get("b64"))

            # If the image data is not None, save it to a temporary file
            if image_data:
                # Open the image data as an image
                image = Image.open(BytesIO(image_data))

                # Save the image to a temporary file
                temp_image_file = NamedTemporaryFile(delete=False, suffix=".jpeg")
                image.save(temp_image_file.name, format="JPEG")

                # Return the path of the temporary file
                return temp_image_file.name
            else:
                # Log an error message
                logging.error("No image data found.")
        except requests.exceptions.RequestException as e:
            # Log the error
            logging.error(f"Request failed: {e}")

            # If this was the last retry, re-raise the exception
            if i == retries - 1:
                raise
        except Exception as e:
            # Log the error and re-raise the exception
            logging.error(e)
            raise

    # If the fetch was unsuccessful, return None
    return None


def fetch_hair_style_image(url: str, hair: str, temp_file_path: str, retries: int = 3) -> Optional[str]:
    """
    This function fetches a hair style image from a given URL.

    Parameters:
    url (str): The URL from which to fetch the hair style image.
    hair (str): The hair style to be used for the image.
    temp_file_path (str): The path of the temporary file to be used for storing the hair style image.
    retries (int, optional): The number of times to retry the fetch if it fails. Defaults to 3.

    Returns:
    Optional[str]: The path of the fetched hair style image if the fetch is successful, None otherwise.

    Raises:
    requests.exceptions.RequestException: If a request to the URL fails.
    Exception: If any other error occurs.
    """
    # Try to fetch the hair style image
    for i in range(retries):
        try:
            # Open the temporary file
            with open(temp_file_path, "rb") as temp_file:
                # Send a POST request to the URL with the hair style and the temporary file
                response = requests.post(
                    url, data={"hair": hair}, files={"file": temp_file}
                )

            # If the request was unsuccessful, raise an exception
            response.raise_for_status()

            # Decode the base64 image data from the response
            image_data = base64.b64decode(response.json().get("b64"))

            # If the image data is not None, save it to a temporary file
            if image_data:
                # Open the image data as an image
                image = Image.open(BytesIO(image_data))

                # Save the image to a temporary file
                temp_image_file = NamedTemporaryFile(delete=False, suffix=".jpeg")
                image.save(temp_image_file.name, format="JPEG")

                # Return the path of the temporary file
                return temp_image_file.name
            else:
                # Log an error message
                logging.error("No image data found.")
        except requests.exceptions.RequestException as e:
            # Log the error
            logging.error(f"Request failed: {e}")

            # If this was the last retry, re-raise the exception
            if i == retries - 1:
                raise
        except Exception as e:
            # Log the error and re-raise the exception
            logging.error(e)
            raise

    # If the fetch was unsuccessful, return None
    return None


def fetch_prod_recs(url: str, temp_file_path: str, retries: int = 3) -> Tuple[Optional[Dict[str, List[Dict]]], Optional[List[str]]]:
    """
    This function fetches product recommendations from a given URL.

    Parameters:
    url (str): The URL from which to fetch the product recommendations.
    temp_file_path (str): The path of the temporary file to be used for storing the product recommendations.
    retries (int, optional): The number of times to retry the fetch if it fails. Defaults to 3.

    Returns:
    Tuple[Optional[Dict[str, List[Dict]]], Optional[List[str]]]: A tuple containing a dictionary of product recommendations and a list of company names if the fetch is successful, (None, None) otherwise.

    Raises:
    requests.exceptions.RequestException: If a request to the URL fails.
    Exception: If any other error occurs.
    """
    # Try to fetch the product recommendations
    for i in range(retries):
        try:
            # Open the temporary file
            with open(temp_file_path, "rb") as temp_file:
                # Send a POST request to the URL with the temporary file
                response = requests.post(url, files={"file": temp_file})

            # If the request was unsuccessful, raise an exception
            response.raise_for_status()

            # Get the product recommendations from the response
            recs = response.json()

            # If the product recommendations are not None, process them
            if recs:
                # Initialize a dictionary for the product recommendations and a set for the company names
                company_products = collections.defaultdict(list)
                company_names = set()

                # Process each product recommendation
                for rec in recs:
                    # Get the company of the product recommendation
                    company = rec["Company"].lower()

                    # If the company is not in the set and the set has less than 10 companies, add the company to the set
                    if len(company_names) < 10:
                        company_names.add(company)

                        # If the company has less than 10 product recommendations, add the product recommendation to the company
                        if len(company_products[company]) < 10:
                            company_products[company].append(rec)

                # Return the product recommendations and the company names
                return company_products, list(company_names)
            else:
                # Log an error message
                logging.error("No product recommendations data found.")
        except requests.exceptions.RequestException as e:
            # Log the error
            logging.error(f"Request failed: {e}")

            # If this was the last retry, re-raise the exception
            if i == retries - 1:
                raise
        except Exception as e:
            # Log the error and re-raise the exception
            logging.error(e)
            raise

    # If the fetch was unsuccessful, return (None, None)
    return None, None


def upload_media(temp_file_path: str, number_id: str, retries: int = 3) -> Optional[str]:
    """
    This function uploads a media file to WhatsApp.

    Parameters:
    temp_file_path (str): The path of the temporary file to be uploaded.
    number_id (str): The ID of the phone number to which the media file is to be uploaded.
    retries (int, optional): The number of times to retry the upload if it fails. Defaults to 3.

    Returns:
    Optional[str]: The ID of the uploaded media file if the upload is successful, None otherwise.

    Raises:
    requests.exceptions.RequestException: If a request to the WhatsApp API fails.
    Exception: If any other error occurs.
    """
    # Get the WhatsApp token and media URL from the environment variables
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    whatsapp_media_url = os.getenv("WHATSAPP_MEDIA_URL")

    # Construct the media URL
    media_url = "{}/{}/media".format(whatsapp_media_url, number_id)

    # Define the headers for the request
    headers = {"Authorization": "Bearer " + whatsapp_token}

    # Define the data for the request
    data = {"messaging_product": "whatsapp"}

    # Try to upload the media file
    for i in range(retries):
        try:
            # Open the temporary file
            with open(temp_file_path, "rb") as temp_file:
                # Determine the file type based on the file extension
                _, ext = os.path.splitext(temp_file_path)
                if ext.lower() == ".jpeg":
                    files = {"file": ("image.jpeg", temp_file, "image/jpeg")}
                elif ext.lower() == ".pdf":
                    files = {"file": ("document.pdf", temp_file, "application/pdf")}
                else:
                    raise ValueError("Unsupported file extension: {}".format(ext))

                # Send a POST request to the media URL with the data and the file
                response = requests.post(
                    media_url, headers=headers, data=data, files=files
                )

            # If the request was unsuccessful, raise an exception
            response.raise_for_status()

            # Get the media ID from the response
            media_id = response.json().get("id")

            # Return the media ID
            return media_id
        except requests.exceptions.RequestException as e:
            # Log the error
            logging.error(f"Request failed: {e}")

            # If this was the last retry, re-raise the exception
            if i == retries - 1:
                raise
        except Exception as e:
            # Log the error and re-raise the exception
            logging.error(e)
            raise

    # If the upload was unsuccessful, return None
    return None


def handle_vto_type(
    vto_type: str,
    number: str,
    last_vto_type: Dict[str, List[str]],
    feats: Dict[str, Dict[str, Dict[str, str]]],
    media_content: str,
    numberId: str,
    messageId: str,
    response_list: List[str],
    hair_color_try_on_edge: str = "",
    lip_stick_try_on_edge: str = "",
    lip_liner_try_on_edge: str = "") -> List[str]:
    """
    This function handles the virtual try-on (VTO) type and generates the appropriate responses.

    Parameters:
    vto_type (str): The type of the VTO.
    number (str): The phone number of the recipient.
    last_vto_type (Dict[str, List[str]]): A dictionary mapping phone numbers to a list of the last VTO types.
    feats (Dict[str, Dict[str, Dict[str, str]]]): A dictionary containing the features for the VTO.
    media_content (str): The media content for the VTO.
    numberId (str): The ID of the phone number.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.
    hair_color_try_on_edge (str, optional): The URL for the hair color try-on. Defaults to an empty string.
    lip_stick_try_on_edge (str, optional): The URL for the lip stick try-on. Defaults to an empty string.
    lip_liner_try_on_edge (str, optional): The URL for the lip liner try-on. Defaults to an empty string.

    Returns:
    List[str]: The updated list of responses.

    Raises:
    Exception: If an error occurs while handling the VTO type.
    """
    try:
        # Send a hold message
        send_hold = pause_text(number)
        response_list.append(send_hold)

        # Get the top level option, company name, and color name from the last VTO type
        top_level_option = last_vto_type[number][-3]
        company_name = last_vto_type[number][-2]
        color_name = last_vto_type[number][-1]

        # Get the hex color code from the features
        hex_color_code = feats[(top_level_option)][(company_name)][(color_name)]

        # Determine the edge URL based on the VTO type
        if "color try-on" in vto_type:
            edge_url = hair_color_try_on_edge
        elif "lip stick try-on" in vto_type:
            edge_url = lip_stick_try_on_edge
        elif "lip liner try-on" in vto_type:
            edge_url = lip_liner_try_on_edge

        # Fetch the VTO image
        temp_file = fetch_vto_image(edge_url, hex_color_code, media_content)

        # Upload the VTO image
        vto_file = upload_media(temp_file, numberId)

        # Send the VTO image
        send_image = image_message(number, vto_file)
        response_list.append(send_image)

        # Send a follow-up message
        check_in = follow_up(number, messageId)
        response_list.append(check_in)

        # Return the updated list of responses
        return response_list
    except Exception as e:
        # Log the error
        logging.error(f"Error occurred while handling VTO type: {e}")

        # Re-raise the exception
        raise


def handle_hair_style(
    number: str, 
    last_hair_type: Dict[str, List[str]], 
    feats: Dict[str, Dict[str, str]], 
    media_content: str, 
    numberId: str, 
    messageId: str, 
    response_list: List[str],
    hair_style_try_on_edge: str = "") -> List[str]:
    """
    This function handles the hair style virtual try-on (VTO) and generates the appropriate responses.

    Parameters:
    number (str): The phone number of the recipient.
    last_hair_type (Dict[str, List[str]]): A dictionary mapping phone numbers to a list of the last hair styles.
    feats (Dict[str, Dict[str, str]]): A dictionary containing the features for the VTO.
    media_content (str): The media content for the VTO.
    numberId (str): The ID of the phone number.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.
    hair_style_try_on_edge (str, optional): The URL for the hair style try-on. Defaults to an empty string.

    Returns:
    List[str]: The updated list of responses.

    Raises:
    Exception: If an error occurs while handling the hair style VTO.
    """
    try:
        # Send a hold message
        send_hold = pause_text(number)
        response_list.append(send_hold)

        # Get the top level option and style name from the last hair style
        top_level_option = last_hair_type[number][-2]
        style_name = last_hair_type[number][-1]

        # Get the hair style code from the features
        hair_style_code = feats[(top_level_option)][(style_name)]

        # Fetch the hair style image
        temp_file = fetch_hair_style_image(
            hair_style_try_on_edge, hair_style_code, media_content
        )

        # Upload the hair style image
        vto_file = upload_media(temp_file, numberId)

        # Send the hair style image
        send_image = image_message(number, vto_file)
        response_list.append(send_image)

        # Send a follow-up message
        check_in = follow_up(number, messageId)
        response_list.append(check_in)

        # Return the updated list of responses
        return response_list
    except Exception as e:
        # Log the error
        logging.error(f"Error occurred while handling hairstyle VTO: {e}")

        # Re-raise the exception
        raise


def fetch_product_recs(
    number: str, 
    rec_type: str, 
    media_content: str, 
    numberId: str, 
    messageId: str, 
    response_list: List[str],
    foundation_recs_edge: str = "",
    skin_tint_try_on_edge: str = "",
    concealer_recs_edge: str = "",
    setting_powder_recs_edge: str = "",
    contour_recs_edge: str = "",
    bronzer_recs_edge: str = "",
    shape_wear_recs_edge: str = "",
    nude_shoes_recs_edge: str = "") -> Tuple[List[str], Dict[str, List[Dict]], List[str]]:
    """
    This function fetches product recommendations based on the type of the product and generates the appropriate responses.

    Parameters:
    number (str): The phone number of the recipient.
    rec_type (str): The type of the product for which to fetch recommendations.
    media_content (str): The media content for the product.
    numberId (str): The ID of the phone number.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.
    foundation_recs_edge (str, optional): The URL for the foundation recommendations. Defaults to an empty string.
    skin_tint_try_on_edge (str, optional): The URL for the skin tint try-on. Defaults to an empty string.
    concealer_recs_edge (str, optional): The URL for the concealer recommendations. Defaults to an empty string.
    setting_powder_recs_edge (str, optional): The URL for the setting powder recommendations. Defaults to an empty string.
    contour_recs_edge (str, optional): The URL for the contour recommendations. Defaults to an empty string.
    bronzer_recs_edge (str, optional): The URL for the bronzer recommendations. Defaults to an empty string.
    shape_wear_recs_edge (str, optional): The URL for the shapewear recommendations. Defaults to an empty string.
    nude_shoes_recs_edge (str, optional): The URL for the nude shoes recommendations. Defaults to an empty string.

    Returns:
    Tuple[List[str], Dict[str, List[Dict]], List[str]]: A tuple containing the updated list of responses, a dictionary of product recommendations, and a list of company names.

    Raises:
    Exception: If an error occurs while fetching the product recommendations.
    """
    try:
        # Send a hold message
        send_hold = pause_text(number)
        response_list.append(send_hold)

        # Determine the edge URL based on the product type
        if "foundation" in rec_type:
            edge_url = foundation_recs_edge
        elif "skin tint" in rec_type:
            edge_url = skin_tint_try_on_edge
        elif "concealer" in rec_type:
            edge_url = concealer_recs_edge
        elif "setting powder" in rec_type:
            edge_url = setting_powder_recs_edge
        elif "contour" in rec_type:
            edge_url = contour_recs_edge
        elif "bronzer" in rec_type:
            edge_url = bronzer_recs_edge
        elif "shapewear" in rec_type:
            edge_url = shape_wear_recs_edge
        elif "nude shoes" in rec_type:
            edge_url = nude_shoes_recs_edge

        # Fetch the product recommendations
        company_products, company_names = fetch_prod_recs(edge_url, media_content)

        # Define the body, footer, and options of the message
        body = "I’m delighted to hear of your interest in exploring options tailored to your skin tone. To provide you with the most suitable recommendations, could you please select one of the following esteemed brands? Each offers a range of products designed to complement and enhance your unique beauty. 🌟"
        footer = "AIySha by roboMUA"
        options = [name.title() for name in company_names]

        # Create a list reply message
        list_reply_data = list_reply_message(
            number, options, body, footer, "brands_product_recs", messageId
        )
        response_list.append(list_reply_data)

        # Return the updated list of responses, the product recommendations, and the company names
        return response_list, company_products, company_names
    except Exception as e:
        # Log the error
        logging.error(f"Error occurred while handling product recommendations: {e}")

        # Re-raise the exception
        raise


def create_pdf(products: List[Dict[str, str]]) -> str:
    """
    This function creates a PDF file with product information.

    Parameters:
    products (List[Dict[str, str]]): A list of dictionaries where each dictionary contains product information.

    Returns:
    str: The path of the created PDF file.
    """
    # Create a BytesIO object to hold the PDF data
    pdf_bytes = BytesIO()

    # Create a canvas for the PDF
    c = canvas.Canvas(pdf_bytes, pagesize=letter)

    # Define the starting coordinates for the text
    x = 50
    y = 750

    # Iterate over each product
    for product in products:
        # Define the keys and labels for the product information
        keys_labels = {
            "Foundation": "Foundation",
            "Shade": "Shade",
            "Concealer": "Concealer",
            "Shoe": "Shoe",
        }

        # Initialize an empty string for the message
        message = ""

        # Iterate over each key and label
        for key, label in keys_labels.items():
            # If the key is in the product, add the product information to the message
            if key in product:
                message = f"🤎 *{label}*: ```{product[key]}```\n" + message

        # Add the price, buy link, and tutorial link to the message
        message += f"💰 *Price*: `{product['Price']}`\n🛍️ *Buy*: ```{product['ProductURL']}```\n🎬 *Tutorial*: ```{product['VideoTutorial']}```\n"

        # Draw the message on the canvas
        c.drawString(x, y, message)

        # Move the y-coordinate down for the next product
        y -= 100

        # If the y-coordinate is too low, create a new page and reset the y-coordinate
        if y < 50:
            c.showPage()
            y = 750

    # Save the PDF data to the canvas
    c.save()

    # Get the PDF data from the BytesIO object
    pdf_data = pdf_bytes.getvalue()

    # Create a temporary file to hold the PDF data
    temp_doc_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    # Write the PDF data to the temporary file
    temp_doc_file.write(pdf_data)

    # Close the temporary file
    temp_doc_file.close()

    # Return the path of the temporary file
    return temp_doc_file.name


def handle_greetings(text: str, number: str, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles greetings and generates the appropriate responses.

    Parameters:
    text (str): The greeting text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.

    Returns:
    List[str]: The updated list of responses.
    """
    # Define the body, footer, and options of the message
    body = "Hello, there! I’m AIySha, your dedicated beauty ally. My mission is to elevate your beauty routine and ensure you feel extraordinary. How may I enhance your allure today? ✨"
    footer = "AIySha by roboMUA"
    options = ["💄 Product Recs", "🪞 Try-On"]

    # Create a button reply message
    reply_button_data = button_reply_message(
        number, options, body, footer, "intro", messageId
    )

    # Create a reply reaction message
    reply_reaction = reply_reaction_message(number, messageId, "❤️")

    # Add the reply reaction and button reply messages to the list of responses
    response_list.append(reply_reaction)
    response_list.append(reply_button_data)

    # Return the updated list of responses
    return response_list


def handle_else_condition(
    text: str,
    number: str,
    messageId: str,
    response_list: List[str],
    chat_history: List[Tuple]) -> Tuple[List[str], List[Tuple]]:
    """
    This function handles the case where the input text does not match any expected conditions and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.
    chat_history (List[Tuple]): A list of tuples containing the chat history.

    Returns:
    # List[str]: The updated list of responses.
    Tuple[List[str], List[Tuple]]: The updated list of responses and the conversation history.
    """
    model_res = get_model_response(text, chat_history)
    body = model_res[0]
    convo_history = model_res[1]
    
    # Create a text message suggesting to reset the conversation
    data = text_message(
        number,
        body
        # "Oops! I didn’t get that. Can you please rephrase your question? 🤔",
    )

    # Add the text message to the list of responses
    response_list.append(data)

    # Return the updated list of responses and chat history
    return response_list, chat_history


def handle_product_recs(text: str, number: str, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles product recommendations and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.

    Returns:
    List[str]: The updated list of responses.
    """
    # Define the body, footer, and options of the message
    body = "How thrilling to embrace your adventurous spirit! Let’s channel that energy into creating a stunning visage that reflects your inner creativity. I’m here to guide you every step of the way. Tell me, what vision do you have for your transformative look today? 🎨✨"
    footer = "AIySha by roboMUA"
    options = ["😀 Face", "☺️ Cheeks", "👤 Body"]

    # Create a list reply message
    list_reply_data = list_reply_message(
        number, options, body, footer, "product_recs", messageId
    )

    # Add the list reply message to the list of responses
    response_list.append(list_reply_data)

    # Return the updated list of responses
    return response_list


def handle_face(text: str, number: str, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles the case where the user wants to focus on their face and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.

    Returns:
    List[str]: The updated list of responses.
    """
    # Define the body, footer, and options of the message
    body = "Indeed, true beauty resonates from within, yet there’s always room to highlight your natural allure with the right products. Allow me to assist you in selecting the perfect items to accentuate your complexion. Could you share which feature of your face you’d like to enhance first? 🌟"
    footer = "AIySha by roboMUA"
    options = ["🎨 Foundation", "🙈 Concealer", "💎 Setting Powder"]  # "🌟 Skin Tint",

    # Create a list reply message
    list_reply_data = list_reply_message(
        number, options, body, footer, "face", messageId
    )

    # Add the list reply message to the list of responses
    response_list.append(list_reply_data)

    # Return the updated list of responses
    return response_list


def handle_cheeks(text: str, number: int, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles the 'cheeks' makeup option in the virtual makeup assistant.
    
    Parameters:
    text (str): The text message from the user.
    number (int): The number associated with the user's message.
    messageId (str): The unique identifier for the user's message.
    response_list (List[str]): The list of responses generated so far.

    Returns:
    List[str]: The updated list of responses after handling the 'cheeks' makeup option.
    """
    
    # Define the body of the message
    body = "Your desire for glamour shines through, and rest assured, I’m here to support your vision. Whether you’re leaning towards a subtle, natural elegance or aiming for the dramatic flair of a diva, I’m at your service. What are your aspirations for today’s look? ✨"
    
    # Define the footer of the message
    footer = "AIySha by roboMUA"
    
    # Define the options for the user
    options = ["😊 Contour", "🥉 Bronzer"]

    # Generate the reply button data
    reply_button_data = button_reply_message(
        number, options, body, footer, "cheeks", messageId
    )
    
    # Append the reply button data to the response list
    response_list.append(reply_button_data)

    # Return the updated response list
    return response_list


def handle_body(text: str, number: int, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles the 'body' fashion option in the virtual fashion assistant.
    
    Parameters:
    text (str): The text message from the user.
    number (int): The number associated with the user's message.
    messageId (str): The unique identifier for the user's message.
    response_list (List[str]): The list of responses generated so far.

    Returns:
    List[str]: The updated list of responses after handling the 'body' fashion option.
    """
    
    # Define the body of the message
    body = "Ah, the beauty sovereign graces us with her presence! Are you prepared to enchant the world with your splendid visage? Share with me, what sort of enchantment shall we conjure up for your look today? ✨"
    
    # Define the footer of the message
    footer = "AIySha by roboMUA"
    
    # Define the options for the user
    options = ["🩱 Shapewear", "🥿 Nude Shoes"]

    # Generate the reply button data
    reply_button_data = button_reply_message(
        number, options, body, footer, "body", messageId
    )
    
    # Append the reply button data to the response list
    response_list.append(reply_button_data)

    # Return the updated response list
    return response_list


def handle_recs_selfie(text: str, number: str, messageId: str, response_list: List[str], last_rec_type: Dict[str, str], *args, **kwargs) -> List[str]:
    """
    This function handles the case where the user is asked to take a selfie to be used to generate the appropriate recommendations.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.
    last_rec_type (Dict[str, str]): A dictionary that stores the last recommendation type for each number.

    Returns:
    List[str]: The updated list of responses.
    """
    # Update the last recommendation type for the given number
    last_rec_type[number] = text

    # Generate a request for a selfie
    selfie_request = ask_for_selfie(number)

    # Add the selfie request to the list of responses
    response_list.append(selfie_request)

    # Return the updated list of responses
    return response_list


def handle_vto(text: str, number: str, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles the case where the user wants to try on a virtual makeover and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.

    Returns:
    List[str]: The updated list of responses.
    """
    # Define the body, footer, and options of the message
    body = "Fantastic! We’re about to embark on a transformative journey with a touch of digital enchantment. Tell me, what ambiance are you aiming to capture with your new look? 🌟✨"
    footer = "AIySha by roboMUA"
    options = ["🪮 Hair", "👄 Lips"]

    # Create a button reply message
    reply_button_data = button_reply_message(
        number, options, body, footer, "vto", messageId
    )

    # Add the button reply message to the list of responses
    response_list.append(reply_button_data)

    # Return the updated list of responses
    return response_list


def handle_hair(text: str, number: str, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles the case where the user wants to try on a virtual hair makeover and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.

    Returns:
    List[str]: The updated list of responses.
    """
    # Define the body, footer, and options of the message
    body = "Marvelous choice! Elevating your look with a fresh hair color or style can be truly transformative. Are you envisioning a bold new shade to make a statement, or perhaps a chic cut to redefine your style? Share your inspiration, and let’s craft a look that’s uniquely you. 🌈✨"
    footer = "AIySha by roboMUA"
    options = ["💈 Color Try-On", "🎀 Style Try-On"]

    # Create a button reply message
    reply_button_data = button_reply_message(
        number, options, body, footer, "hair", messageId
    )

    # Add the button reply message to the list of responses
    response_list.append(reply_button_data)

    # Return the updated list of responses
    return response_list


def handle_lips(text: str, number: str, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles the case where the user wants to try on a virtual lips makeover and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.

    Returns:
    List[str]: The updated list of responses.
    """
    # Define the body, footer, and options of the message
    body = "Absolutely, let’s revitalize your beauty routine! For lips that make a statement, are you feeling the boldness of a fiery red, or perhaps the understated elegance of a nude shade? Remember, a good lipliner is your ally—it ensures your lipstick stays precisely where it should. Ready to define your look? 💄✨"
    footer = "AIySha by roboMUA"
    options = ["💋 Lip Stick Try-On", "🫦 Lip Liner Try-On"]

    # Create a button reply message
    reply_button_data = button_reply_message(
        number, options, body, footer, "lips", messageId
    )

    # Add the button reply message to the list of responses
    response_list.append(reply_button_data)

    # Return the updated list of responses
    return response_list


def handle_digit_text(text: str, number: str, messageId: str, numberId: str, response_list: List[str], last_rec_type: Dict[str, str], last_vto_type: Dict[str, str], last_hair_type: Dict[str, str]) -> List[str]:
    """
    This function handles the case where the user sends a photo (usually selfie) or an image and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    numberId (str): The ID of the number.
    response_list (List[str]): A list of responses to be sent.
    last_rec_type (Dict[str, str]): A dictionary that stores the last recommendation type for each number.
    last_vto_type (Dict[str, str]): A dictionary that stores the last VTO type for each number.
    last_hair_type (Dict[str, str]): A dictionary that stores the last hair type for each number.

    Returns:
    List[str]: The updated list of responses.
    """
    # Try to download the media content from the text
    try:
        media_content = download_media(text, numberId)
    except Exception as e:
        logging.error(e)

    # If the media content is not None
    if media_content is not None:
        # Get the last recommendation type, VTO type, and hair type for the given number
        rec_type = last_rec_type.get(number)
        vto_type = last_vto_type.get(number)
        hair_type = last_hair_type.get(number)

        # If the last recommendation type is in all image options
        if rec_type and any(option in rec_type for option in all_image_options):
            (
                response_list,
                recs_data["company_products"],
                recs_data["company_names"],
            ) = fetch_product_recs(
                number, rec_type, media_content, numberId, messageId, response_list
            )
        # If the last VTO type is in plus color options
        elif vto_type and any(option in vto_type for option in plus_color_options):
            response_list = handle_vto_type(
                vto_type,
                number,
                last_vto_type,
                feats,
                media_content,
                numberId,
                messageId,
                response_list,
            )
        # If the last hair type is "style try-on"
        elif hair_type and "style try-on" in hair_type:
            response_list = handle_hair_style(
                number,
                last_hair_type,
                feats,
                media_content,
                numberId,
                messageId,
                response_list,
            )
        # If none of the above conditions are met
        else:
            send_text = text_message(
                number,
                "Oops, this photo came in at the wrong time. I can't work on this right now. Could you please send me another selfie after you tell me what product you're looking for? Or after you choose a VTO option? Pretty please?",
            )
            response_list.append(send_text)

        # If the number is in the last recommendation type, delete it
        if number in last_rec_type:
            del last_rec_type[number]

        # If the number is in the last VTO type, delete it
        if number in last_vto_type:
            del last_vto_type[number]

        # If the number is in the last hair type, delete it
        if number in last_hair_type:
            del last_hair_type[number]

    # Return the updated list of responses
    return response_list


def handle_yes_please(text: str, number: str, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles the case where the user responds with "yes please" and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.

    Returns:
    List[str]: The updated list of responses.
    """
    # Define the body, footer, and options of the message
    body = "You’re truly in the spirit of transformation! With our virtual beauty wand at the ready, what new look or style would you like to bring to life? Let’s create some beauty magic together! 🪄✨"
    footer = "AIySha by roboMUA"
    options = ["💄 Product Recs", "🪞 Try-On"]

    # Create a button reply message
    reply_button_data = button_reply_message(
        number, options, body, footer, "intro", messageId
    )

    # Add the button reply message to the list of responses
    response_list.append(reply_button_data)

    # Return the updated list of responses
    return response_list


def handle_no_thanks(text: str, number: str, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles the case where the user responds with "no thanks" and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.

    Returns:
    List[str]: The updated list of responses.
    """
    # Define the text message to be sent
    send_text = text_message(
        number,
        textwrap.dedent(
            """
            Absolutely! Don’t forget to snag our app for: 
            `iOS` ```@ https://apps.apple.com/us/app/robomua/id6443639738```
            `Android` ```@ https://play.google.com/store/apps/details?id=com.domainname.roboMUANEW```
            It’s like having a genie in your pocket – minus the three-wish limit. I’m just a text away, ready to grant your digital wishes. Catch you on the flip side! 😄🧞‍♂️✨
            """
        ),
    )

    # Add the text message to the list of responses
    response_list.append(send_text)

    # Return the updated list of responses
    return response_list


def handle_company_names(text: str, number: str, messageId: str, name: str, response_list: List[str], recs_data: Dict[str, Dict[str, List[Dict[str, str]]]]) -> List[str]:
    """
    This function handles the case where the user wants to get recommendations from specific companies and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    name (str): The name of the recipient.
    response_list (List[str]): A list of responses to be sent.
    recs_data (Dict[str, Dict[str, List[Dict[str, str]]]]): A dictionary that stores the company names and products for each number.

    Returns:
    List[str]: The updated list of responses.
    """
    # Get the products from the company specified in the text
    products = recs_data["company_products"].get(text, [])

    # If the number of products is more than 5
    if len(products) > 5:
        # Create a PDF file with the products
        rec_file = create_pdf(products)

        # Upload the PDF file
        doc_file = upload_media(rec_file, numberId)

        # Create a document message with the PDF file
        send_doc = document_message(
            number,
            doc_file,
            "Your Recommendations",
            "{}'s Recommendations.pdf".format(name),
        )

        # Add the document message to the list of responses
        response_list.append(send_doc)
    # If the number of products is less than or equal to 5
    else:
        # For each product
        for product in products:
            # Define the keys and labels
            keys_labels = {
                "Foundation": "Foundation",
                "Shade": "Shade",
                "Concealer": "Concealer",
                "Shoe": "Shoe",
            }
            message = ""

            # For each key and label
            for key, label in keys_labels.items():
                # If the key is in the product
                if key in product:
                    # Add the label and the value of the key to the message
                    message = f"🤎 *{label}*: ```{product[key]}```\n" + message

            # Add the price, buy link, and tutorial link to the message
            message += f"💰 *Price*: `{product['Price']}`\n🛍️ *Buy*: ```{product['ProductURL']}```\n🎬 *Tutorial*: ```{product['VideoTutorial']}```\n"

            # Create a text message with the message
            send_text = text_message(number, message)

            # Add the text message to the list of responses
            response_list.append(send_text)

    # If "company_names" and "company_products" are in recs_data
    if "company_names" in recs_data and "company_products" in recs_data:
        # Clear the company names and products
        recs_data["company_names"] = []
        recs_data["company_products"] = {}

    # Create a follow-up message
    check_in = follow_up(number, messageId)

    # Add the follow-up message to the list of responses
    response_list.append(check_in)

    # Return the updated list of responses
    return response_list


def handle_style_try_on(text: str, number: str, messageId: str, response_list: List[str], last_hair_type: Dict[str, List[str]], feats: Dict[str, Dict[str, str]], *args, **kwargs) -> List[str]:
    """
    This function handles the case where the user wants to try on a virtual hair style and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.
    last_hair_type (Dict[str, List[str]]): A dictionary that stores the last hair type for each number.
    feats (Dict[str, Dict[str, str]]): A dictionary that stores the features for each text.

    Returns:
    List[str]: The updated list of responses.
    """
    # Add the text to the last hair type for the given number
    last_hair_type.setdefault(number, []).append(text)

    # Define the body, footer, and options of the message
    body = "Navigating to the hair salon, it’s time to redefine your look! Shall we go bold with a daring pixie cut, embrace the romance of flowing mermaid waves, or perhaps choose a hue that embodies ‘rockstar’ vibes? Together, we’ll craft an experience that elevates your hair to new heights of style! 💇‍♀️🎨🤘"
    footer = "AIySha by roboMUA"
    options = [name.title() for name in feats[text].keys()]

    # Create a list reply message
    list_reply_data = list_reply_message(
        number, options, body, footer, "vto_opt_3", messageId
    )

    # Add the list reply message to the list of responses
    response_list.append(list_reply_data)

    # Return the updated list of responses
    return response_list


def handle_style_selfie(text: str, number: str, response_list: List[str], last_hair_type: Dict[str, List[str]]) -> List[str]:
    """
    This function handles the case where the user is requested to take a selfie for a virtual hair style and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    response_list (List[str]): A list of responses to be sent.
    last_hair_type (Dict[str, List[str]]): A dictionary that stores the last hair type for each number.

    Returns:
    List[str]: The updated list of responses.
    """
    # Add the text to the last hair type for the given number
    last_hair_type[number].append(text)

    # Generate a request for a selfie
    selfie_request = ask_for_selfie(number)

    # Add the selfie request to the list of responses
    response_list.append(selfie_request)

    # Return the updated list of responses
    return response_list


def handle_plus_color_options(text: str, number: str, messageId: str, response_list: List[str], last_vto_type: Dict[str, List[str]], feats: Dict[str, Dict[str, str]], *args, **kwargs) -> List[str]:
    """
    This function handles the case where the user wants to try on a virtual lipstick, lip liner or hair color option and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.
    last_vto_type (Dict[str, List[str]]): A dictionary that stores the last VTO type for each number.
    feats (Dict[str, Dict[str, str]]): A dictionary that stores the features for each text.

    Returns:
    List[str]: The updated list of responses.
    """
    # Add the text to the last VTO type for the given number
    last_vto_type.setdefault(number, []).append(text)

    # Define the body, footer, and options of the message
    body = "Envision yourself in a boutique of beauty, surrounded by the finest brands, each offering a delightful selection to satisfy your style cravings. Which one captures your heart and transports you to a realm of fashion enchantment? 🍭👗✨"
    footer = "AIySha by roboMUA"
    options = [name.title() for name in feats[text].keys()]

    # Create a list reply message
    list_reply_data = list_reply_message(
        number, options, body, footer, "vto_opt_1", messageId
    )

    # Add the list reply message to the list of responses
    response_list.append(list_reply_data)

    # Return the updated list of responses
    return response_list


def handle_vto_options(text: str, number: str, messageId: str, response_list: List[str], last_vto_type: Dict[str, List[str]], feats: Dict[str, Dict[str, Dict[str, str]]]) -> List[str]:
    """
    This function handles the case where the user wants to try on a virtual option and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.
    last_vto_type (Dict[str, List[str]]): A dictionary that stores the last VTO type for each number.
    feats (Dict[str, Dict[str, Dict[str, str]]]): A dictionary that stores the features for each text.

    Returns:
    List[str]: The updated list of responses.
    """
    # Add the text to the last VTO type for the given number
    last_vto_type[number].append(text)

    # Define the body, footer, and options of the message
    body = "Selecting the perfect shade is akin to donning a superhero’s cape—each color holds its own power and story. So, which hue will be your superpower today? Will it be a bold, confident red or perhaps a mysterious, deep blue? Let’s find the color that makes you feel invincible! 🦸‍♂️🌈"
    footer = "AIySha by roboMUA"
    options = [key.title() for key in feats[last_vto_type[number][0]][text].keys()]

    # Create a list reply message
    list_reply_data = list_reply_message(
        number, options, body, footer, "vto_opt_2", messageId
    )

    # Add the list reply message to the list of responses
    response_list.append(list_reply_data)

    # Return the updated list of responses
    return response_list


def handle_vto_selfie(text: str, number: str, response_list: List[str], last_vto_type: Dict[str, List[str]]) -> List[str]:
    """
    This function handles the case where the user is asked to take a selfie for a virtual try-on (VTO) and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    response_list (List[str]): A list of responses to be sent.
    last_vto_type (Dict[str, List[str]]): A dictionary that stores the last VTO type for each number.

    Returns:
    List[str]: The updated list of responses.
    """
    # Add the text to the last VTO type for the given number
    last_vto_type[number].append(text)

    # Generate a request for a selfie
    selfie_request = ask_for_selfie(number)

    # Add the selfie request to the list of responses
    response_list.append(selfie_request)

    # Return the updated list of responses
    return response_list


def get_variables():
    """
    This function returns the variables 'last_vto_type', 'recs_data', and 'feats' which are required for the 'manage_chatbot' function.

    Returns:
    last_vto_type (dict): A dictionary to store the last VTO (Virtual Try-On) type for each number.
    recs_data (dict): A dictionary to store the company names and products for each number.
    feats (dict): A dictionary that stores the features for each text.

    Note: The actual definitions of 'last_vto_type', 'recs_data', and 'feats' should be present in the scope where this function is defined.
    """
    # Returning the variables 'last_vto_type', 'recs_data', and 'feats'
    return last_vto_type, recs_data, feats


# A dictionary to store the last recommendation type for each number
last_rec_type = {}

# A dictionary to store the last VTO (Virtual Try-On) type for each number
last_vto_type = {}

# A dictionary to store the last hair type for each number
last_hair_type = {}

# A dictionary to store the company names and products for each number
recs_data = {"company_names": [], "company_products": {}}


def manage_chatbot(text: str, number: str, messageId: str, name: str, numberId: str, last_vto_type: Dict[str, List[str]], recs_data: Dict[str, List[str]], feats: Dict[str, Dict[str, Dict[str, str]]]) -> None:
    """
    This function manages the chatbot by handling different types of user inputs and generating the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    name (str): The name of the recipient.
    numberId (str): The ID of the number.
    last_vto_type (Dict[str, List[str]]): A dictionary that stores the last VTO type for each number.
    recs_data (Dict[str, List[str]]): A dictionary that stores the company names and products for each number.
    feats (Dict[str, Dict[str, Dict[str, str]]]): A dictionary that stores the features for each text.

    Returns:
    None
    """
    # Convert the text to lower case
    text = text.lower()

    # Remove emojis and strip the text
    stripped_text = remove_emoji_and_strip(text)

    # Initialize the list of responses
    response_list = []
    
    # Initialize the list of chat history
    chat_history = []

    # Initialize the temporary files
    downloaded_temp_file = None
    temp_image_file = None
    temp_doc_file = None

    # Mark the message as read
    mark_read = mark_read_message(messageId)
    response_list.append(mark_read)

    # Define the handlers for different types of user inputs
    handlers = {
        "greetings": handle_greetings,
        "product recs": handle_product_recs,
        "face": handle_face,
        "cheeks": handle_cheeks,
        "body": handle_body,
        "try-on": handle_vto,
        "hair": handle_hair,
        "lips": handle_lips,
        "style try-on": handle_style_try_on,
        "yes, please.": handle_yes_please,
        "no, thanks.": handle_no_thanks,
        "foundation": handle_recs_selfie,
        "skin tint": handle_recs_selfie,
        "concealer": handle_recs_selfie,
        "setting powder": handle_recs_selfie,
        "contour": handle_recs_selfie,
        "bronzer": handle_recs_selfie,
        "shapewear": handle_recs_selfie,
        "nude shoes": handle_recs_selfie,
        "color try-on": handle_plus_color_options,
        "lip stick try-on": handle_plus_color_options,
        "lip liner try-on": handle_plus_color_options,
        "box braids": handle_style_selfie,
        "kinky twist": handle_style_selfie,
        "lemonade braids": handle_style_selfie,
        "bantu knots": handle_style_selfie,
        "wavy bob": handle_style_selfie,
        "high top fade": handle_style_selfie,
        "buzz cut": handle_style_selfie,
        "twist out": handle_style_selfie,
        "wash n go": handle_style_selfie,
        "pixie cut": handle_style_selfie,
        "digit text": handle_digit_text,
        "company names": handle_company_names,
        "vto options": handle_vto_options,
        "vto selfie": handle_vto_selfie,
    }
    
    params = {
        'handle_style_try_on': {'last_hair_type': last_hair_type, 'feats': feats},
        'handle_plus_color_options': {'last_vto_type': last_vto_type, 'feats': feats},
        'handle_recs_selfie': {'last_rec_type': last_rec_type}
    }
    
    # For each keyword and handler in the handlers
    for keyword, handler in handlers.items():
        # If the keyword is "greetings" and the text is a greeting
        if keyword == "greetings" and any(greeting in text for greeting in greetings):
            response_list = handler(text, number, messageId, response_list)

        # If the keyword is the stripped text
        elif keyword in stripped_text:
            if handler in params:
                response_list = handler(stripped_text, number, messageId, response_list, **params[handler])
            else:
                response_list = handler(stripped_text, number, messageId, response_list)
            
        # If the keyword is the text
        elif keyword in text:
            response_list = handler(text, number, response_list)

        # If the keyword is "digit text" and the text is a digit
        elif keyword == "digit text" and text.isdigit():
            response_list = handler(text, number, messageId, numberId, response_list)

        # If the keyword is "company names" and the text is a company name
        elif keyword == "company names" and any(
            option in text for option in recs_data["company_names"]
        ):
            response_list = handler(text, number, messageId, name, response_list)

        # If the keyword is "vto options" and the text is a VTO option
        elif keyword == "vto options" and any(
            option in text for option in feats[last_vto_type[number][0]].keys()
        ):
            response_list = handler(text, number, messageId, response_list)

        # If the keyword is "vto selfie" and the text is a VTO selfie option
        elif keyword == "vto selfie" and any(
            option in text
            for option in feats[last_vto_type[number][0]][
                last_vto_type[number][-1]
            ].keys()
        ):
            response_list = handler(text, number, response_list)
        
        # If none of the above conditions are met, use the "else" handler
        else:
            continue
            # response_list = handle_else_condition(text, number, messageId, response_list)
            # res = handle_else_condition(text, number, messageId, response_list, chat_history)
            # response_list = res[0]
            # chat_history = res[1]
            
        break
    # else:
    #     # response_list = handle_else_condition(text, number, messageId, response_list)
    #     res = handle_else_condition(text, number, messageId, response_list, chat_history)
    #     response_list = res[0]
    #     chat_history = res[1]

    # For each item in the list of responses, send a WhatsApp message
    for item in response_list:
        send_whatsapp_message(item)

    # If the downloaded temporary file exists, remove it
    if downloaded_temp_file is not None and os.path.isfile(downloaded_temp_file.name):
        os.remove(downloaded_temp_file.name)

    # If the temporary image file exists, remove it
    if temp_image_file is not None and os.path.isfile(temp_image_file.name):
        os.remove(temp_image_file.name)

    # If the temporary document file exists, remove it
    if temp_doc_file is not None and os.path.isfile(temp_doc_file.name):
        os.remove(temp_doc_file.name)
