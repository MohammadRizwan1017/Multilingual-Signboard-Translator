from flask import Flask, request, jsonify, render_template, send_file
import cv2
import pytesseract
import speech_recognition as sr
from googletrans import Translator
from gtts import gTTS
import os
import time

app = Flask(__name__)

# Directories for uploads and audio files
UPLOAD_FOLDER = 'static/uploads'
AUDIO_FOLDER = 'static/audio'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Supported languages and corresponding Tesseract OCR models
OCR_LANGUAGES = {'en': 'eng', 'hi': 'hin', 'ta': 'tam', 'bn': 'ben',
                 'te': 'tel', 'kn': 'kan', 'ml': 'mal', 'mr': 'mar'}

# Funtion to check image clarity using Laplacian variance
def is_image_clear(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    fm = cv2.Laplacian(gray, cv2.CV_64F).var()
    return fm >= 100

# Function to extract text from image using Tesseract OCR
def extract_text_from_image(image_path):
    extracted_texts = {}
    for lang_code, tesseract_lang in OCR_LANGUAGES.items():
        text = pytesseract.image_to_string(cv2.imread(image_path), lang=tesseract_lang).strip()
        if text:
            extracted_texts[lang_code] = text
    return extracted_texts

# Function to extract text from live audio using SpeechRecognition
def extract_text_from_live_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio_data = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            return "Could not understand audio."
        except sr.RequestError:
            return "Speech recognition service unavailable."

# Function to translate text 
def translate_text(text, target_language):
    translator = Translator()
    translated = translator.translate(text, dest=target_language)
    return translated.text if translated and translated.text.strip() else "Translation not available."

# Function to convert translated text to speech
def text_to_speech(text, lang):
    tts = gTTS(text=text, lang=lang)
    filename = f"speech_{int(time.time())}.mp3"
    audio_path = os.path.join(AUDIO_FOLDER, filename)
    tts.save(audio_path)
    return filename

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        target_lang = request.form.get('language', 'en')  # ensure language is always captured

        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            if not is_image_clear(filepath):
                return jsonify({"message": "The picture is not clear."})

            extracted_texts = extract_text_from_image(filepath)
            if not extracted_texts:
                return jsonify({"message": "No recognizable text found."})

            detected_lang, extracted_text = next(iter(extracted_texts.items()))

        elif request.form.get('live_audio') == 'true':
            extracted_text = extract_text_from_live_audio()
            detected_lang = "en"

        else:
            return jsonify({"message": "No input provided. Please upload an image or speak live."})

        translated_text = translate_text(extracted_text, target_lang)
        audio_filename = text_to_speech(translated_text, target_lang)
        audio_url = f"/audio/{audio_filename}"

        return jsonify({
            "detected_language": detected_lang,
            "extracted_text": extracted_text,
            "translated_text": translated_text,
            "audio_url": audio_url
        })

    return render_template('index.html')

@app.route('/audio/<filename>')
def get_audio(filename):
    return send_file(os.path.join(AUDIO_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
