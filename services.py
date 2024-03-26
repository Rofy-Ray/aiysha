# -*- coding: utf-8 -*-
import requests
import json
import time
import os
import logging
import base64
import collections
import textwrap
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


def get_whatsapp_message(message):
    if "type" not in message:
        text = "message not recognized."
        return text

    typeMessage = message["type"]
    if typeMessage == "text":
        text = message["text"]["body"]
    elif typeMessage == "image":
        text = message["image"]["id"]
    elif typeMessage == "button":
        text = message["button"]["text"]
    elif (
        typeMessage == "interactive" and message["interactive"]["type"] == "list_reply"
    ):
        text = message["interactive"]["list_reply"]["title"]
    elif (
        typeMessage == "interactive"
        and message["interactive"]["type"] == "button_reply"
    ):
        text = message["interactive"]["button_reply"]["title"]
    else:
        text = "message not processed."

    return text


def send_whatsapp_message(data):
    try:
        whatsapp_token = os.getenv("WHATSAPP_TOKEN")
        flask_env = os.getenv("FLASK_ENV")
        whatsapp_url = (
            os.getenv("WHATSAPP_URL_DEV")
            if flask_env == "development"
            else os.getenv("WHATSAPP_URL_PROD")
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + whatsapp_token,
        }
        response = requests.post(whatsapp_url, headers=headers, data=data)
        response.raise_for_status()
        time.sleep(5)
        return "message sent!", 200
    except requests.HTTPError as http_err:
        return "HTTP error occurred: {}".format(http_err), response.status_code
    except Exception as err:
        return "Other error occurred: {}".format(err), 403


def text_message(number, text):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "text",
            "text": {"body": text},
        }
    )
    return data


def button_reply_message(number, options, body, footer, scenario, messageId):
    buttons = []
    for i, option in enumerate(options):
        buttons.append(
            {
                "type": "reply",
                "reply": {"id": scenario + "_btn_" + str(i + 1), "title": option},
            }
        )

    data = json.dumps(
        {
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
    )
    return data


def list_reply_message(number, options, body, footer, scenario, messageId):
    rows = []
    for i, option in enumerate(options):
        rows.append(
            {"id": scenario + "_row_" + str(i + 1), "title": option, "description": ""}
        )

    data = json.dumps(
        {
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
    )
    return data


def document_message(number, docId, caption, filename):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "document",
            "document": {"id": docId, "caption": caption, "filename": filename},
        }
    )
    return data


def image_message(number, image_id):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "image",
            "image": {"id": image_id},
        }
    )
    return data


def sticker_message(number, sticker_id):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "sticker",
            "sticker": {"id": sticker_id},
        }
    )
    return data


def get_media_id(media_name, media_type):
    media_id = ""
    if media_type == "sticker":
        media_id = STICKER_ID.get(media_name, None)
    elif media_type == "image":
        media_id = IMAGE_ID.get(media_name, None)
    elif media_type == "video":
        media_id = VIDEO_ID.get(media_name, None)
    elif media_type == "audio":
        media_id = AUDIO_ID.get(media_name, None)
    return media_id


def reply_reaction_message(number, messageId, emoji):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "reaction",
            "reaction": {"message_id": messageId, "emoji": emoji},
        }
    )
    return data


def reply_text_message(number, messageId, text):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "context": {"message_id": messageId},
            "type": "text",
            "text": {"body": text},
        }
    )
    return data


def mark_read_message(messageId):
    data = json.dumps(
        {"messaging_product": "whatsapp", "status": "read", "message_id": messageId}
    )
    return data


def ask_for_selfie(number):
    try:
        send_text = text_message(
            number,
            "Great! Now, I need to see your beautiful face in all its glory. Please snap a selfie and send it to me. But make sure you're not wearing any makeup or glasses. I want to see the real you, not the filtered version.",
        )
        return send_text
    except Exception as e:
        logging.error("Error occurred while asking for selfie: {}".format(e))


def pause_text(number):
    try:
        send_text = text_message(
            number,
            "Hang tight! I’m whipping up some digital wizardry as we speak. It’s like a techy cauldron bubbling with bytes and bits – your wish is my command line. 🧙‍♂️💻✨",
        )
        return send_text
    except Exception as e:
        logging.error("Error occurred while asking user to hold on: {}".format(e))


def follow_up(number, messageId):
    body = "You were absolutely dazzling! But the show must go on, right? What’s the next act in your personal style saga that I can assist with? 🌟🎭✨"
    footer = "AIySha by roboMUA"
    options = ["✅ Yes, please.", "❌ No, thanks."]

    reply_button_data = button_reply_message(
        number, options, body, footer, "scenario4", messageId
    )
    return reply_button_data


def remove_emoji_and_strip(input_string):
    return input_string[2:].strip()


def download_media(media_id, number_id, retries=3):
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    whatsapp_media_url = os.getenv("WHATSAPP_MEDIA_URL")
    media_url = "{}/{}?phone_number_id={}".format(
        whatsapp_media_url, media_id, number_id
    )
    headers = {"Authorization": "Bearer " + whatsapp_token}

    for i in range(retries):
        try:
            response = requests.get(media_url, headers=headers)
            response.raise_for_status()
            media_data = response.json()
            media_url = media_data.get("url")
            if media_url:
                response = requests.get(media_url, headers=headers)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
                downloaded_temp_file = NamedTemporaryFile(delete=False, suffix=".jpeg")
                image.save(downloaded_temp_file.name, format="JPEG")
                return downloaded_temp_file.name
        except requests.exceptions.RequestException as e:
            logging.error("Request failed: {}".format(e))
            if i == retries - 1:
                raise
        except Exception as e:
            logging.error(e)
            raise


def fetch_vto_image(url, color, temp_file_path, retries=3):
    for i in range(retries):
        try:
            with open(temp_file_path, "rb") as temp_file:
                response = requests.post(
                    url, data={"color": color}, files={"file": temp_file}
                )
            response.raise_for_status()
            image_data = base64.b64decode(response.json().get("b64"))
            if image_data:
                image = Image.open(BytesIO(image_data))
                temp_image_file = NamedTemporaryFile(delete=False, suffix=".jpeg")
                image.save(temp_image_file.name, format="JPEG")
                return temp_image_file.name
            else:
                logging.error("No image data found.")
        except requests.exceptions.RequestException as e:
            logging.error("Request failed: {}".format(e))
            if i == retries - 1:
                raise
        except Exception as e:
            logging.error(e)
            raise
    return None


def fetch_hair_style_image(url, hair, temp_file_path, retries=3):
    for i in range(retries):
        try:
            with open(temp_file_path, "rb") as temp_file:
                response = requests.post(
                    url, data={"hair": hair}, files={"file": temp_file}
                )
            response.raise_for_status()
            image_data = base64.b64decode(response.json().get("b64"))
            if image_data:
                image = Image.open(BytesIO(image_data))
                temp_image_file = NamedTemporaryFile(delete=False, suffix=".jpeg")
                image.save(temp_image_file.name, format="JPEG")
                return temp_image_file.name
            else:
                logging.error("No image data found.")
        except requests.exceptions.RequestException as e:
            logging.error("Request failed: {}".format(e))
            if i == retries - 1:
                raise
        except Exception as e:
            logging.error(e)
            raise
    return None


def fetch_prod_recs(url, temp_file_path, retries=3):
    for i in range(retries):
        try:
            with open(temp_file_path, "rb") as temp_file:
                response = requests.post(url, files={"file": temp_file})
            response.raise_for_status()
            recs = response.json()
            if recs:
                company_products = collections.defaultdict(list)
                company_names = set()
                for rec in recs:
                    company = rec["Company"].lower()
                    if len(company_names) < 10:
                        company_names.add(company)
                        if len(company_products[company]) < 10:
                            company_products[company].append(rec)
                return company_products, list(company_names)
            else:
                logging.error("No product recommendations data found.")
        except requests.exceptions.RequestException as e:
            logging.error("Request failed: {}".format(e))
            if i == retries - 1:
                raise
        except Exception as e:
            logging.error(e)
            raise
    return None, None


def upload_media(temp_file_path, number_id, retries=3):
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    whatsapp_media_url = os.getenv("WHATSAPP_MEDIA_URL")
    media_url = "{}/{}/media".format(whatsapp_media_url, number_id)
    headers = {"Authorization": "Bearer " + whatsapp_token}

    data = {"messaging_product": "whatsapp"}
    for i in range(retries):
        try:
            with open(temp_file_path, "rb") as temp_file:
                _, ext = os.path.splitext(temp_file_path)
                if ext.lower() == ".jpeg":
                    files = {"file": ("image.jpeg", temp_file, "image/jpeg")}
                elif ext.lower() == ".pdf":
                    files = {"file": ("document.pdf", temp_file, "application/pdf")}
                else:
                    raise ValueError("Unsupported file extension: {}".format(ext))
                response = requests.post(
                    media_url, headers=headers, data=data, files=files
                )
            response.raise_for_status()
            media_id = response.json().get("id")
            return media_id
        except requests.exceptions.RequestException as e:
            logging.error("Request failed: {}".format(e))
            if i == retries - 1:
                raise
        except Exception as e:
            logging.error(e)
            raise
    return None


def handle_vto_type(
    vto_type,
    number,
    last_vto_type,
    feats,
    media_content,
    numberId,
    messageId,
    response_list,):
    try:
        send_hold = pause_text(number)
        response_list.append(send_hold)
        top_level_option = last_vto_type[number][-3]
        company_name = last_vto_type[number][-2]
        color_name = last_vto_type[number][-1]
        hex_color_code = feats[(top_level_option)][(company_name)][(color_name)]

        if "color try-on" in vto_type:
            edge_url = hair_color_try_on_edge
        elif "lip stick try-on" in vto_type:
            edge_url = lip_stick_try_on_edge
        elif "lip liner try-on" in vto_type:
            edge_url = lip_liner_try_on_edge

        temp_file = fetch_vto_image(edge_url, hex_color_code, media_content)
        vto_file = upload_media(temp_file, numberId)
        send_image = image_message(number, vto_file)
        response_list.append(send_image)
        check_in = follow_up(number, messageId)
        response_list.append(check_in)
        return response_list
    except Exception as e:
        logging.error("Error occurred while handling VTO type: {}".format(e))


def handle_hair_style(
    number, last_hair_type, feats, media_content, numberId, messageId, response_list):
    try:
        send_hold = pause_text(number)
        response_list.append(send_hold)
        top_level_option = last_hair_type[number][-2]
        style_name = last_hair_type[number][-1]
        hair_style_code = feats[(top_level_option)][(style_name)]

        temp_file = fetch_hair_style_image(
            hair_style_try_on_edge, hair_style_code, media_content
        )
        vto_file = upload_media(temp_file, numberId)
        send_image = image_message(number, vto_file)
        response_list.append(send_image)
        check_in = follow_up(number, messageId)
        response_list.append(check_in)
        return response_list
    except Exception as e:
        llogging.error("Error occurred while handling hairstyle VTO: {}".format(e))


def fetch_product_recs(
    number, rec_type, media_content, numberId, messageId, response_list):
    try:
        send_hold = pause_text(number)
        response_list.append(send_hold)

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

        company_products, company_names = fetch_prod_recs(edge_url, media_content)

        body = "I have a lot of recommendations for you. Please choose one of the following companies to see their products that match your skin shade."
        footer = "AIySha by roboMUA"
        options = [name.title() for name in company_names]

        list_reply_data = list_reply_message(
            number, options, body, footer, "brands_product_recs", messageId
        )
        response_list.append(list_reply_data)

        return response_list, company_products, company_names
    except Exception as e:
        llogging.error(
            "Error occurred while handling product recommendations: {}".format(e)
        )


def create_pdf(products):
    pdf_bytes = BytesIO()

    c = canvas.Canvas(pdf_bytes, pagesize=letter)

    x = 50
    y = 750

    for product in products:
        text = textwrap.dedent(
            """
            🤎 *Foundation*: ```{foundation}```
            💰 *Price*: `{price}`
            🛍️ *Buy*: ```{product_url}```
            🎬 *Tutorial*: ```{video_tutorial}```
            """.format(
                foundation=product["Foundation"],
                price=product["Price"],
                product_url=product["ProductURL"],
                video_tutorial=product["VideoTutorial"],
            )
        )

        c.drawString(x, y, text)

        y -= 100

        if y < 50:
            c.showPage()
            y = 750

    c.save()

    pdf_data = pdf_bytes.getvalue()

    temp_doc_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_doc_file.write(pdf_data)
    temp_doc_file.close()

    return temp_doc_file.name


def handle_greetings(text, number, messageId, response_list):
    body = "Greetings, gorgeous!👋🏿 I'm AIySha, your roboMUA BFF. I'm here to make you look and feel fabulous. What can I do for you today?"
    footer = "AIySha by roboMUA"
    options = ["💄 Product Recs", "🪞 Try-On"]

    reply_button_data = button_reply_message(
        number, options, body, footer, "intro", messageId
    )
    reply_reaction = reply_reaction_message(number, messageId, "❤️")

    response_list.append(reply_reaction)
    response_list.append(reply_button_data)

    return response_list


def handle_else_condition(text, number, messageId, response_list):
    data = text_message(
        number,
        "Oops, you lost me there. How about we switch gears and hit the reset button?",
    )
    response_list.append(data)

    return response_list


def handle_product_recs(text, number, messageId, response_list):
    body = "Oh, I see you're feeling adventurous today. Ready to unleash your inner artist and transform your face into a masterpiece? Don't worry, I'll guide you through the process. What kind of look are you going for?"
    footer = "AIySha by roboMUA"
    options = ["😀 Face", "👀 Eyes", "☺️ Cheeks", "👤 Body"]

    list_reply_data = list_reply_message(
        number, options, body, footer, "product_recs", messageId
    )

    response_list.append(list_reply_data)

    return response_list


def handle_face(text, number, messageId, response_list):
    body = "You know what they say, beauty is skin deep. But that doesn't mean you can't enhance it with some awesome products. Let me help you find the ones that suit your complexion. Which part of your face do you want to focus on first?"
    footer = "AIySha by roboMUA"
    options = ["🎨 Foundation", "🙈 Concealer", "💎 Setting Powder"]  # "🌟 Skin Tint",

    list_reply_data = list_reply_message(
        number, options, body, footer, "face", messageId
    )
    response_list.append(list_reply_data)

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
    options = ["🧴 Scents", "🩱 Shapewear", "🥿 Nude Shoes"]

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
    options = ["💈 Color Try-On"]  # , "🎀 Style Try-On"

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
            messageId = textwrap.dedent(
                """
                🤎 *Foundation*: ```{foundation}```
                💰 *Price*: `{price}`
                🛍️ *Buy*: ```{product_url}```
                🎬 *Tutorial*: ```{video_tutorial}```
                """.format(
                    foundation=product["Foundation"],
                    price=product["Price"],
                    product_url=product["ProductURL"],
                    video_tutorial=product["VideoTutorial"],
                )
            )
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


def handle_style_selfie(text, number, messageId, response_list):
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


def handle_vto_selfie(text, number, messageId, response_list):
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
        "digit text": handle_digit_text,
        "company names": handle_company_names,
        "vto options": handle_vto_options,
        "vto selfie": handle_vto_selfie,
        # "hairstyle selfie": handle_style_selfie,
        # "recs selfie": handle_recs_selfie,
        # "plus color options": handle_plus_color_options,
        "else": handle_else_condition,
    }

    for keyword, handler in handlers.items():
        if keyword == "greetings" and any(greeting == text for greeting in greetings):
            response_list = handler(text, number, messageId, response_list)

        elif keyword == stripped_text:
            response_list = handler(stripped_text, number, messageId, response_list)

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
            response_list = handler(text, number, messageId, response_list)

        # elif keyword == "hairstyle selfie" and any(option in text for option in feats[last_hair_type[number][0]].keys()):
        #     response_list = handler(text, number, messageId, response_list)

        # elif keyword == "recs selfie" and stripped_text in all_image_options:
        #     response_list = handler(stripped_text, number, messageId, response_list)

        # elif keyword == "plus color options" and stripped_text in plus_color_options:
        #     response_list = handler(stripped_text, number, messageId, response_list)

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
