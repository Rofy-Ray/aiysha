# -*- coding: utf-8 -*-
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

load_dotenv()

logging.basicConfig(level=logging.INFO)

with open("options.json") as f:
    feats = json.load(f)

config = configparser.ConfigParser()
config.read("config.ini")

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
    This function creates a text message asking the user to wait.

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
    body = "You were absolutely dazzling! But the show must go on, right? Is there a next act in your personal style saga that I can assist with? 🌟🎭✨"
    footer = "AIySha by roboMUA"
    options = ["✅ Yes, please.", "❌ No, thanks."]

    # Create a button reply message
    reply_button_data = button_reply_message(
        number, options, body, footer, "scenario4", messageId
    )

    return reply_button_data


def remove_emoji_and_strip(input_string: str) -> str:
    """
    This function removes the first two characters (usually an emoji) from a string and then removes any leading or trailing whitespace.

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
        body = "I have a lot of recommendations for you. Please choose one of the following companies to see their products that match your skin shade."
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
    body = "Greetings, gorgeous!👋🏿 I'm AIySha, your roboMUA BFF. I'm here to make you look and feel fabulous. What can I do for you today?"
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


def handle_else_condition(text: str, number: str, messageId: str, response_list: List[str]) -> List[str]:
    """
    This function handles the case where the input text does not match any expected conditions and generates the appropriate responses.

    Parameters:
    text (str): The input text.
    number (str): The phone number of the recipient.
    messageId (str): The ID of the message.
    response_list (List[str]): A list of responses to be sent.

    Returns:
    List[str]: The updated list of responses.
    """
    # Create a text message suggesting to reset the conversation
    data = text_message(
        number,
        "Oops, you lost me there. How about we switch gears and hit the reset button?",
    )

    # Add the text message to the list of responses
    response_list.append(data)

    # Return the updated list of responses
    return response_list


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
    body = "Oh, I see you're feeling adventurous today. Ready to unleash your inner artist and transform your face into a masterpiece? Don't worry, I'll guide you through the process. What kind of look are you going for?"
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
    body = "You know what they say, beauty is skin deep. But that doesn't mean you can't enhance it with some awesome products. Let me help you find the ones that suit your complexion. Which part of your face do you want to focus on first?"
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


def handle_cheeks(text, number, messageId, response_list):
    body = "I see you're in the mood for some glam. Don't worry, I've got you covered. Whether you want to go for a natural look or a full-on diva, I'm here to help. So, what's the plan, Stan?"
    footer = "AIySha by roboMUA"
    options = ["😊 Contour", "🥉 Bronzer"]

    reply_button_data = button_reply_message(
        number, options, body, footer, "cheeks", messageId
    )
    response_list.append(reply_button_data)

    return response_list


def handle_body(text, number, messageId, response_list):
    body = "Well, well, well, if it isn't the beauty queen herself. Ready to dazzle the world with your fabulous face? Tell me, what kind of magic are we working with today?"
    footer = "AIySha by roboMUA"
    options = ["🩱 Shapewear", "🥿 Nude Shoes"]

    reply_button_data = button_reply_message(
        number, options, body, footer, "body", messageId
    )
    response_list.append(reply_button_data)

    return response_list


def handle_recs_selfie(text, number, messageId, response_list):
    last_rec_type[number] = text

    selfie_request = ask_for_selfie(number)
    response_list.append(selfie_request)

    return response_list


def handle_vto(text, number, messageId, response_list):
    body = "Awesome! Let's give you a new look with some digital magic. What kind of vibe are you going for?"
    footer = "AIySha by roboMUA"
    options = ["🪮 Hair", "👄 Lips"]

    reply_button_data = button_reply_message(
        number, options, body, footer, "vto", messageId
    )
    response_list.append(reply_button_data)

    return response_list


def handle_hair(text, number, messageId, response_list):
    body = "Cool! Let's spice up your look with some hair color or style changes. What are you in the mood for?"
    footer = "AIySha by roboMUA"
    options = ["💈 Color Try-On", "🎀 Style Try-On"]

    reply_button_data = button_reply_message(
        number, options, body, footer, "hair", messageId
    )
    response_list.append(reply_button_data)

    return response_list


def handle_lips(text, number, messageId, response_list):
    body = "O-kay! Looks like we’re mixing up our beauty stations. For lips that pop, are we thinking bold and daring with a fiery red, or classic chic with a nude shade? And don’t forget the lipliner – it’s the secret agent that keeps your lipstick from going rogue. 💄🕵️‍♀️✨"
    footer = "AIySha by roboMUA"
    options = ["💋 Lip Stick Try-On", "🫦 Lip Liner Try-On"]

    reply_button_data = button_reply_message(
        number, options, body, footer, "lips", messageId
    )
    response_list.append(reply_button_data)

    return response_list


def handle_digit_text(text, number, messageId, numberId, response_list):
    try:
        media_content = download_media(text, numberId)
    except Exception as e:
        logging.error(e)
    if media_content is not None:
        rec_type = last_rec_type.get(number)
        vto_type = last_vto_type.get(number)
        hair_type = last_hair_type.get(number)
        if rec_type and any(option in rec_type for option in all_image_options):
            (
                response_list,
                recs_data["company_products"],
                recs_data["company_names"],
            ) = fetch_product_recs(
                number, rec_type, media_content, numberId, messageId, response_list
            )
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
        else:
            send_text = text_message(
                number,
                "Oops, this photo came in at the wrong time. I can't work on this right now. Could you please send me another selfie after you tell me what product you're looking for? Or after you choose a VTO option? Pretty please?",
            )
            response_list.append(send_text)
        if number in last_rec_type:
            del last_rec_type[number]

        if number in last_vto_type:
            del last_vto_type[number]

        if number in last_hair_type:
            del last_hair_type[number]

    return response_list


def handle_yes_please(text, number, messageId, response_list):
    body = "You’re on a roll! It’s like we’ve got a magic wand for fun – just wave it and poof! What’s the next adventure you’d like to conjure up? 🪄✨"
    footer = "AIySha by roboMUA"
    options = ["💄 Product Recs", "🪞 Try-On"]

    reply_button_data = button_reply_message(
        number, options, body, footer, "intro", messageId
    )
    response_list.append(reply_button_data)

    return response_list


def handle_no_thanks(text, number, messageId, response_list):
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
    response_list.append(send_text)

    return response_list


def handle_company_names(text, number, messageId, name, response_list):
    products = recs_data["company_products"].get(text, [])
    if len(products) > 5:
        rec_file = create_pdf(products)
        doc_file = upload_media(rec_file, numberId)
        send_doc = document_message(
            number,
            doc_file,
            "Your Recommendations",
            "{}'s Recommendations.pdf".format(name),
        )
        response_list.append(send_doc)
    else:
        for product in products:
            keys_labels = {
                "Foundation": "Foundation",
                "Shade": "Shade",
                "Concealer": "Concealer",
                "Shoe": "Shoe",
            }
            message = ""

            for key, label in keys_labels.items():
                if key in product:
                    message = f"🤎 *{label}*: ```{product[key]}```\n" + message

            message += f"💰 *Price*: `{product['Price']}`\n🛍️ *Buy*: ```{product['ProductURL']}```\n🎬 *Tutorial*: ```{product['VideoTutorial']}```\n"

            send_text = text_message(number, message)
            response_list.append(send_text)

    if "company_names" in recs_data and "company_products" in recs_data:
        recs_data["company_names"] = []
        recs_data["company_products"] = {}

    check_in = follow_up(number, messageId)
    response_list.append(check_in)

    return response_list


def handle_style_try_on(text, number, messageId, response_list):
    last_hair_type.setdefault(number, []).append(text)

    body = "Whoops, let’s steer our style compass towards the hair salon! Are we thinking a daring pixie cut, or perhaps flowing mermaid waves? Maybe even a color that screams ‘rockstar’? Let’s create a ‘hair-raising’ experience! 💇‍♀️🎨🤘"
    footer = "AIySha by roboMUA"
    options = [name.title() for name in feats[text].keys()]

    list_reply_data = list_reply_message(
        number, options, body, footer, "vto_opt_3", messageId
    )
    response_list.append(list_reply_data)

    return response_list


def handle_style_selfie(text, number, response_list):
    last_hair_type[number].append(text)

    selfie_request = ask_for_selfie(number)
    response_list.append(selfie_request)

    return response_list


def handle_plus_color_options(text, number, messageId, response_list):
    last_vto_type.setdefault(number, []).append(text)

    body = "Got it! It’s like we’re in a candy store of brands, and you’re about to pick the sweetest treat. So, which one makes you feel like a kid in a fashion wonderland? 🍭👗✨"
    footer = "AIySha by roboMUA"
    options = [name.title() for name in feats[text].keys()]

    list_reply_data = list_reply_message(
        number, options, body, footer, "vto_opt_1", messageId
    )
    response_list.append(list_reply_data)

    return response_list


def handle_vto_options(text, number, messageId, response_list):
    last_vto_type[number].append(text)

    body = "Brilliant pick! It’s like choosing a superhero costume – so, which shade of awesome are we going for today? 🦸‍♂️🌈"
    footer = "AIySha by roboMUA"
    options = [key.title() for key in feats[last_vto_type[number][0]][text].keys()]

    list_reply_data = list_reply_message(
        number, options, body, footer, "vto_opt_2", messageId
    )
    response_list.append(list_reply_data)

    return response_list


def handle_vto_selfie(text, number, response_list):
    last_vto_type[number].append(text)

    selfie_request = ask_for_selfie(number)
    response_list.append(selfie_request)

    return response_list


last_rec_type = {}
last_vto_type = {}
last_hair_type = {}
recs_data = {"company_names": [], "company_products": {}}


def manage_chatbot(text, number, messageId, name, numberId):
    text = text.lower()
    stripped_text = remove_emoji_and_strip(text)
    response_list = []
    downloaded_temp_file = None
    temp_image_file = None
    temp_doc_file = None

    mark_read = mark_read_message(messageId)
    response_list.append(mark_read)

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
        "hair out": handle_style_selfie,
        "afro": handle_style_selfie,
        "box braids": handle_style_selfie,
        "twist curls": handle_style_selfie,
        "bantu knots": handle_style_selfie,
        "high top fade": handle_style_selfie,
        "weave cap": handle_style_selfie,
        "digit text": handle_digit_text,
        "company names": handle_company_names,
        "vto options": handle_vto_options,
        "vto selfie": handle_vto_selfie,
        # "hairstyle selfie": handle_style_selfie,
        "else": handle_else_condition,
    }

    for keyword, handler in handlers.items():
        if keyword == "greetings" and any(greeting == text for greeting in greetings):
            response_list = handler(text, number, messageId, response_list)

        elif keyword == stripped_text:
            response_list = handler(stripped_text, number, messageId, response_list)
            
        elif keyword == text:
            response_list = handler(text, number, response_list)

        elif keyword == "digit text" and text.isdigit():
            response_list = handler(text, number, messageId, numberId, response_list)

        elif keyword == "company names" and any(
            option in text for option in recs_data["company_names"]
        ):
            response_list = handler(text, number, messageId, name, response_list)

        elif keyword == "vto options" and any(
            option in text for option in feats[last_vto_type[number][0]].keys()
        ):
            response_list = handler(text, number, messageId, response_list)

        elif keyword == "vto selfie" and any(
            option in text
            for option in feats[last_vto_type[number][0]][
                last_vto_type[number][-1]
            ].keys()
        ):
            response_list = handler(text, number, response_list)
            
        # elif keyword == "hairstyle selfie" and any(
        #     option == text for option in feats[last_hair_type[number][0]].keys()
        # ):
        #     response_list = handler(text, number, response_list)

        else:
            continue
        break
    else:
        response_list = handlers["else"]

    for item in response_list:
        send_whatsapp_message(item)

    if downloaded_temp_file is not None and os.path.isfile(downloaded_temp_file.name):
        os.remove(downloaded_temp_file.name)

    if temp_image_file is not None and os.path.isfile(temp_image_file.name):
        os.remove(temp_image_file.name)

    if temp_doc_file is not None and os.path.isfile(temp_doc_file.name):
        os.remove(temp_doc_file.name)
