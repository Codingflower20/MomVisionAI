from flask import Flask, render_template, request, send_from_directory, jsonify
from google.cloud import vision
import json
from firebase_admin import storage
import firebase_admin
from firebase_admin import credentials
import datetime
import logging
import google.generativeai as genai
from google.cloud import texttospeech_v1 as texttospeech
import os


# Initialize Firebase Admin SDK (Ensure this is done only once)
cred = credentials.Certificate("firebase-credentials.json") # Replace with your credentials file
try:
    firebase_admin.initialize_app(cred, {'storageBucket': 'momvisionai-1.firebasestorage.app'}) # Replace with your bucket name
except ValueError as e:
    if str(e) == 'The default FirebaseApp instance already exists. This means you called initialize_app() more than once without providing an app name as the second argument. The default FirebaseApp instance was not initialized because the extra FirebaseApp instance names are empty.':
        pass  # App already initialized
    else:
        raise


# Initialize Flask app
app = Flask(__name__)
app.logger.setLevel(logging.DEBUG) # Set the logging level
app.config['STATIC_FOLDER'] = 'static' # Explicitly set the static folder


# Initialize Gemini API
genai.configure(api_key="AIzaSyC7wlf6Re-4rDXMTixy4pQaZSAP87g88BA") # Replace with your Gemini API key
model = genai.GenerativeModel('gemini-2.0-flash-001')


# Initialize Google Cloud Text-to-Speech client
tts_client = texttospeech.TextToSpeechClient()


def synthesize_speech(text, language_code="en-IN", voice_name=None, output_filename="speech.mp3"):
    """Synthesizes speech from the input text using Google Cloud TTS."""
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name # Optional: specify a particular voice
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )


    response = tts_client.synthesize_speech(
        request={"input": input_text, "voice": voice, "audio_config": audio_config}
    )


    filepath = os.path.join(app.config['STATIC_FOLDER'], output_filename)
    with open(filepath, "wb") as out:
        out.write(response.audio_content)
        print(f'Audio content written to "{filepath}"')
    return output_filename


def get_firebase_download_url(bucket_name, image_name):
    """
    Generates a signed download URL for the image in Firebase Storage.
    """
    bucket = storage.bucket(bucket_name)
    blob = bucket.blob(image_name)
    url = blob.generate_signed_url(expiration=datetime.timedelta(days=1), method='GET')
    app.logger.debug(f"Generated download URL: {url}")
    return url


def identify_food(image_url):
    """
    Identifies the food item with the second highest confidence
    using the Google Cloud Vision API.
    """
    client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = image_url


    app.logger.debug(f"Vision API image URL: {image_url}")


    response = client.label_detection(image=image)
    labels = response.label_annotations


    app.logger.debug(f"Vision API output: {labels}")


    # Sort labels by confidence in descending order
    sorted_labels = sorted(labels, key=lambda label: label.score, reverse=True)


    second_highest_confident_food = None


    # Iterate through the sorted labels and find the second highest confident safe food
    count = 0
    for label in sorted_labels:
        food = label.description.lower()
        count += 1
        if count == 2:
            second_highest_confident_food = food
            break


    return second_highest_confident_food


def get_food_details(food_name, language='en'):
    """
    Uses Gemini to get more details about the identified food in the specified language.
    """
    prompt_en = f"Tell me more about {food_name}. Include information about its nutritional benefits, and benefits during pregnancy, in about 200 words."
    prompt_hi = f"{food_name}के बारे में मुझे और बताएँ। इसके पोषण संबंधी लाभों और गर्भावस्था के दौरान होने वाले लाभों के बारे में जानकारी शामिल करें। लगभग 100 शब्दों में।"
    prompt = prompt_hi if language == 'hi' else prompt_en
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        app.logger.error(f"Error getting Gemini details for {food_name} in {language}: {e}")
        return "Could not retrieve detailed information at this time."


def get_food_details_gemini(food_name, language='en'):
    """
    Uses Gemini to get more details about the identified food, including safety and vitamins.
    """
    prompt_en = f"""Based on the food item identified as: "{food_name}", provide a brief (one sentence) general assessment of whether it typically appears safe to eat for a pregnant person, considering common visual indicators and local context. Include a disclaimer that this is based on visual appearance only and not a definitive safety assessment.
            Then, in a separate sentence, list the major vitamins commonly found in {food_name}.
    """
    prompt_hi = f"""पहचाने गए खाद्य पदार्थ: "{food_name}" के आधार पर, एक संक्षिप्त (एक वाक्य) सामान्य मूल्यांकन प्रदान करें कि क्या यह आमतौर पर गर्भवती व्यक्ति के लिए खाने के लिए सुरक्षित दिखता है, सामान्य दृश्य संकेतकों और स्थानीय संदर्भ पर विचार करते हुए। इसमें एक अस्वीकरण शामिल करें कि यह केवल दृश्य उपस्थिति पर आधारित है और निश्चित सुरक्षा मूल्यांकन नहीं है।


    फिर, एक अलग वाक्य में, {food_name} में आमतौर पर पाए जाने वाले प्रमुख विटामिनों की सूची दें।
    """
    prompt = prompt_hi if language == 'hi' else prompt_en
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        app.logger.error(f"Error getting Gemini details for {food_name} in {language}: {e}")
        return "Could not retrieve detailed information at this time."


@app.route('/')
def home():
    """
    Handles the main route ('/') of the Flask app.
    """
    return render_template('index.html') # Just render the upload form


@app.route('/analyze_uploaded_image', methods=['POST'])
def analyze_uploaded_image():
    """Handles the analysis of an image uploaded to Firebase Storage."""
    data = request.get_json()
    image_url = data.get('image_url')


    if not image_url:
        return jsonify({'error': 'No image URL provided'}), 400


    food = identify_food(image_url)
    food_details_en = None
    food_details_hi = None
    english_audio_url = None
    hindi_audio_url = None
    safety_assessment = None
    major_vitamins = None
    safety_assessment_hi = None
    major_vitamins_hi = None


    if food:
        gemini_output_en = get_food_details_gemini(food, language='en')
        en_parts = gemini_output_en.split('\n\n')
        if len(en_parts) >= 2:
            safety_assessment = en_parts[0].strip()
            major_vitamins = en_parts[1].replace("Major vitamins:", "").strip()
            food_details_en = f"Safety Assessment: {safety_assessment}\n\nMajor Vitamins: {major_vitamins}\n\nFurther Details: {get_food_details(food, language='en')}"
        else:
            food_details_en = f"Could not reliably extract safety and vitamin information. Further Details: {get_food_details(food, language='en')}"
            safety_assessment = "Information unavailable."
            major_vitamins = "Information unavailable."


        gemini_output_hi = get_food_details_gemini(food, language='hi')
        hi_parts = gemini_output_hi.split('\n\n')
        if len(hi_parts) >= 2:
            safety_assessment_hi = hi_parts[0].strip()
            major_vitamins_hi = hi_parts[1].replace("प्रमुख विटामिन:", "").strip()
            food_details_hi = f"सुरक्षा आकलन: {safety_assessment_hi}\n\nप्रमुख विटामिन: {major_vitamins_hi}\n\nअतिरिक्त जानकारी: {get_food_details(food, language='hi')}"
        else:
            food_details_hi = f"सुरक्षा और विटामिन की जानकारी विश्वसनीय रूप से नहीं निकाली जा सकी। अतिरिक्त जानकारी: {get_food_details(food, language='hi')}"
            safety_assessment_hi = "जानकारी अनुपलब्ध।"
            major_vitamins_hi = "जानकारी अनुपलब्ध।"


        english_text = f"Identified food: {food}. Safety assessment: {safety_assessment}. Major vitamins: {major_vitamins}."
        hindi_text = f"{food} पहचाना गया। सुरक्षा आकलन: {safety_assessment_hi}। प्रमुख विटामिन: {major_vitamins_hi}।"


        english_audio_file = synthesize_speech(english_text, language_code="en-IN", voice_name="en-IN-Wavenet-D", output_filename=f"{food}_en_{datetime.datetime.now().timestamp()}.mp3".replace(" ", "_"))
        english_audio_url = f"/static/{english_audio_file}"


        hindi_audio_file = synthesize_speech(hindi_text, language_code="hi-IN", voice_name="hi-IN-Wavenet-D", output_filename=f"{food}_hi_{datetime.datetime.now().timestamp()}.mp3".replace(" ", "_"))
        hindi_audio_url = f"/static/{hindi_audio_file}"


        return jsonify({
            'food': food,
            'safety_assessment': safety_assessment,
            'major_vitamins': major_vitamins,
            'details_en': food_details_en,
            'details_hi': food_details_hi,
            'english_audio_url': english_audio_url,
            'hindi_audio_url': hindi_audio_url,
            'safety_assessment_hi': safety_assessment_hi,
            'major_vitamins_hi': major_vitamins_hi
        })
    else:
        english_audio_file = synthesize_speech("Food not recognized.", language_code="en-IN", output_filename=f"not_recognized_en_{datetime.datetime.now().timestamp()}.mp3")
        english_audio_url = f"/static/{english_audio_file}"
        hindi_audio_file = synthesize_speech("खाना नहीं पहचाना गया।", language_code="hi-IN", output_filename=f"not_recognized_hi_{datetime.datetime.now().timestamp()}.mp3")
        hindi_audio_url = f"/static/{hindi_audio_file}"
        return jsonify({
            'food': None,
            'safety_assessment': "Food not recognized.",
            'major_vitamins': None,
            'details_en': None,
            'details_hi': None,
            'english_audio_url': english_audio_url,
            'hindi_audio_url': hindi_audio_url,
            'safety_assessment_hi': "खाना नहीं पहचाना गया।",
            'major_vitamins_hi': None
        })


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.config['STATIC_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True)

