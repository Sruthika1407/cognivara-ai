import pytesseract
from flask import Flask, render_template, request
from datetime import datetime
import re
import requests
from dotenv import load_dotenv
import os
load_dotenv()
from transformers import pipeline

generator = pipeline(
    "text2text-generation",
    model="google/flan-t5-small"
)


# PDF + Image
from PyPDF2 import PdfReader
from PIL import Image

app = Flask(__name__)
 
def generate_ai_content(text):

    # 1️⃣ Simplification
    simplification_prompt = f"""
    Read the FULL lesson carefully and simplify the entire lesson in easy student-friendly language.
    Do not summarize only the first paragraph. Cover all the main ideas.

    Lesson:
    {text}
    """
    simplification_response = generator(
        simplification_prompt,
        max_length=600,
        min_length=200,
        do_sample=True
    )
    simplification = simplification_response[0]["generated_text"]

    # 2️⃣ Story
    story_prompt = f"Turn this lesson into a short creative story for students:\n{text}"
    story_response = generator(story_prompt, max_length=300)
    story = story_response[0]["generated_text"]

    # 3️⃣ Bullet Points
    bullet_prompt = f"""
    Read the lesson below and write exactly 5 short bullet points.
    Each bullet point must be on a new line.

    Lesson:
    {text}
    """

    import re
    # 3️⃣ Bullet Points (split sentences from original text)
    sentences = text.split(".")

    clean_bullets = []

    for s in sentences:
        s = s.strip()
        s = s.lstrip('"')
        s = s.lstrip('.')
    
        if s:
            clean_bullets.append("• " + s)

    bullets = "\n".join(clean_bullets)

    return simplification.strip(), story.strip(), bullets.strip()
# ---------------------------------
# TOPIC DETECTOR (UNCHANGED)
# ---------------------------------
def detect_topic(text):
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())

    stopwords = {
        "the", "is", "are", "was", "were", "has", "have", "had",
        "a", "an", "of", "in", "to", "and", "for", "with", "by"
    }

    for word in words:
        if word not in stopwords and len(word) > 4:
            return word.capitalize()

    return "General Topic"

# ---------------------------------
# HOME PAGE (UNCHANGED UI LOGIC)
# ---------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        extracted_text = ""

        # IMAGE
        image = request.files.get("image")
        if image and image.filename:
            try:
                img = Image.open(image)
                extracted_text += pytesseract.image_to_string(img)
            except:
                pass  # avoids crash on Render

        # PDF
        pdf = request.files.get("pdf")
        if pdf and pdf.filename:
            reader = PdfReader(pdf)
            for page in reader.pages:
                extracted_text += page.extract_text() or ""

        # PASTED TEXT
        pasted = request.form.get("text")
        if pasted:
            extracted_text += pasted

        return render_template(
            "loading.html",
            content=extracted_text
        )

    return render_template("index.html")

# ---------------------------------
# RESULT PAGE (AI Integrated)
# ---------------------------------
@app.route('/result', methods=['GET','POST'])
def result():
    text = request.form.get("content", "")

    simplification, story, bullets = generate_ai_content(text)

    return render_template(
        "result.html",
        simplification=simplification,
        story=story,
        bullets=bullets,
        topic=detect_topic(text),
        date=datetime.now().strftime("%d %B %Y")
    )

# ---------------------------------
# RUN SERVER
# ---------------------------------
if __name__ == "__main__":
    app.run(debug=True)

