import json
import os
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"error": f"Server Error: {str(e)}"}), 500

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(APP_ROOT, "history.json")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/v1/completions")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

SPECIALIST_TYPES = {
    "Cardiologist": [
        "heart issues", "high blood pressure", "cholesterol", "ECG", "chest pain", "cardiac",
    ],
    "Endocrinologist": [
        "blood sugar", "thyroid", "hormone", "insulin", "diabetes", "endocrine"],
    "Pulmonologist": ["lung", "respiratory", "asthma", "COPD", "oxygen", "pneumonia"],
    "Neurologist": ["headache", "migraine", "nervous", "brain", "seizure", "stroke"],
    "Gastroenterologist": ["liver", "digestion", "stomach", "hepatitis", "ulcer", "colon"],
    "Nephrologist": ["kidney", "creatinine", "urea", "renal", "glomerular", "dialysis"],
}


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r", encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError:
            return []


def save_history(history):
    with open(HISTORY_PATH, "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2, ensure_ascii=False)


def parse_ai_output(response_text):
    """Extract structured fields from the AI's response."""
    specialist = "General Physician"
    severity = "Unknown"
    for line in response_text.split('\n'):
        if "**Recommended Specialist:**" in line:
            # Extracts "Cardiologist" from "**Recommended Specialist:** Cardiologist"
            specialist = line.split(":", 1)[1].strip()
        elif "**Issue Severity Level:**" in line:
            # Extracts "High" from "**Issue Severity Level:** High"
            severity = line.split(":", 1)[1].strip()
            
    return specialist, severity


def get_prompt(report_text, city, language="English"):
    if language.lower() == "hindi":
        return (
            "आप एक चिकित्सा सहायक हैं जो रोगियों को प्रयोगशाला रिपोर्ट समझने और अगले कदम सुझाने में मदद करते हैं। "
            "सबसे पहले, जांचें कि क्या निम्नलिखित पाठ एक चिकित्सा रिपोर्ट, प्रयोगशाला रिपोर्ट या प्रिस्क्रिप्शन है। "
            "यदि यह कोई चिकित्सा दस्तावेज नहीं है, तो कृपया ठीक 'NOT_A_MEDICAL_REPORT' उत्तर दें और कुछ नहीं। "
            "अन्यथा, निम्नलिखित चिकित्सा रिपोर्ट का विश्लेषण करें और एक स्पष्ट, रोगी के अनुकूल सारांश प्रदान करें। "
            "शामिल करें: मुख्य निष्कर्ष, सलाह के बाद के कदम, और किस विशेषज्ञ को देखने की आवश्यकता है।\n\n"
            f"चिकित्सा रिपोर्ट:\n{report_text}\n\n"
            f"शहर: {city}\n\n"
            "कृपया इस शहर में विशेषज्ञ डॉक्टरों या अस्पतालों के लिए शीर्ष सुझाव भी प्रदान करें, जिन्हें एक बुलेटेड सूची के रूप में स्वरूपित किया गया हो। "
            "डॉक्टरों और अस्पतालों की सूची को [HIGHLIGHT] और [/HIGHLIGHT] के बीच रखें।\n"
            "अपने उत्तर का अंत निम्नलिखित से करें:\n"
            "**सारांश समस्या:** [समस्या का एक वाक्य सारांश]\n"
            "**समस्या का स्तर:** [कम/मध्यम/उच्च/गंभीर]\n"
            "**सुझाए गए विशेषज्ञ:** [Cardiologist/Endocrinologist/Pulmonologist/Neurologist/Gastroenterologist/Nephrologist]\n"
            "**तत्काल कार्रवाई:** [तुरंत क्या करना चाहिए]"
        )
    else:
        return (
            "You are a medical assistant helping patients understand lab reports and suggest next steps. "
            "First, verify if the following text is a medical report, lab report, or prescription. "
            "If it is NOT a medical document, reply with EXACTLY 'NOT_A_MEDICAL_REPORT' and nothing else. "
            "Otherwise, analyze the following medical report and return a clear, patient-friendly summary. "
            "Include: key findings, severity level, recommended next steps, and which specialist to consult. "
            "If the report is incomplete, say so and recommend a follow-up consultation.\n\n"
            f"Medical report:\n{report_text}\n\n"
            f"City: {city}\n\n"
            "Please also provide top suggestions for specialist doctors or hospitals in this city, formatted as a bulleted list. "
            "Wrap the ENTIRE list of doctors and hospitals exactly between [HIGHLIGHT] and [/HIGHLIGHT] tags.\n"
            "End your response with:\n"
            "**Summarized Issue:** [One sentence summary of the main issue]\n"
            "**Issue Severity Level:** [Low/Moderate/High/Critical]\n"
            "**Recommended Specialist:** [Cardiologist/Endocrinologist/Pulmonologist/Neurologist/Gastroenterologist/Nephrologist]\n"
            "**Immediate Action:** [What should be done immediately]"
        )


def call_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def call_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
    }

    normalized_url = OLLAMA_URL.rstrip('/')
    if normalized_url.endswith('/v1/completions'):
        base_url = normalized_url[: -len('/v1/completions')]
    elif normalized_url.endswith('/completions'):
        base_url = normalized_url[: -len('/completions')]
    else:
        base_url = normalized_url

    candidate_urls = [normalized_url]
    if normalized_url.endswith('/v1/completions'):
        candidate_urls.append(base_url + '/completions')
    elif normalized_url.endswith('/completions'):
        candidate_urls.append(base_url + '/v1/completions')
    else:
        candidate_urls.append(base_url + '/v1/completions')
        candidate_urls.append(base_url + '/completions')

    # Remove duplicates while preserving order
    seen = set()
    candidate_urls = [url for url in candidate_urls if not (url in seen or seen.add(url))]

    def fetch_available_models():
        try:
            model_url = base_url.rstrip('/') + '/v1/models'
            response = requests.get(model_url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return [item.get('id') for item in data.get('data', []) if item.get('id')]
        except Exception:
            return []

    tried_models = set()
    model_candidates = [OLLAMA_MODEL] if OLLAMA_MODEL else []
    if not model_candidates:
        model_candidates.append(None)

    last_error = None
    available_models = None

    for model in model_candidates:
        if model in tried_models:
            continue
        tried_models.add(model)
        if model:
            payload['model'] = model
        else:
            payload.pop('model', None)

        for url in candidate_urls:
            try:
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=120,
                )
                if response.status_code == 404:
                    try:
                        error_data = response.json()
                    except ValueError:
                        error_data = {}
                    error_message = error_data.get('error', {}).get('message') if isinstance(error_data, dict) else None
                    if error_message and 'model' in error_message and 'not found' in error_message:
                        if available_models is None:
                            available_models = fetch_available_models()
                        for available_model in available_models:
                            if available_model not in tried_models:
                                model_candidates.append(available_model)
                        last_error = RuntimeError(
                            f"Ollama model '{model}' not found. Available: {available_models}"
                        )
                        break
                    last_error = RuntimeError(f"404 from {url}: {response.text[:200]}")
                    continue
                if response.status_code >= 400:
                    last_error = RuntimeError(f"Ollama returned {response.status_code} for {url}: {response.text[:200]}")
                    continue
                data = response.json()
                if isinstance(data, dict):
                    choices = data.get("choices") or []
                    if choices:
                        first_choice = choices[0]
                        if isinstance(first_choice, dict):
                            return (
                                first_choice.get("message", {}).get("content")
                                or first_choice.get("text")
                                or first_choice.get("content")
                            )
                    return data.get("output") or data.get("completion") or json.dumps(data)
                return str(data)
            except requests.ConnectionError as conn_err:
                last_error = conn_err
                continue
            except Exception as exc:
                last_error = exc
                continue

    raise RuntimeError(
        f"Unable to reach Ollama on any checked URL: {candidate_urls}. "
        f"Models tried: {list(tried_models)}. "
        f"Last error: {last_error}"
    )


def call_ai(report_text, city, language="English"):
    prompt = get_prompt(report_text, city, language)
    if GROQ_API_KEY:
        try:
            return call_groq(prompt)
        except Exception as e:
            # Optionally log the error here. If Groq fails, we can either fall back to Ollama or just fail.
            # We will let it fail so the user knows if their API key is broken.
            raise RuntimeError(f"Groq API Error: {str(e)}")
    else:
        return call_ollama(prompt)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    body = request.form
    report_text = body.get("reportText", "").strip()
    city = body.get("city", "").strip()
    language = body.get("language", "English").strip()
    file = request.files.get("reportFile")

    if not report_text and file:
        filename = file.filename.lower()
        file_bytes = file.read()
        
        if filename.endswith(".pdf"):
            try:
                import PyPDF2
                import io
                reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                pdf_text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        pdf_text += extracted + "\n"
                report_text = pdf_text.strip()
                
                # Fallback to OCR if PDF has no extractable text
                if not report_text:
                    try:
                        import pytesseract
                        import os
                        tess_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                        if os.path.exists(tess_path):
                            pytesseract.pytesseract.tesseract_cmd = tess_path
                        
                        from pdf2image import convert_from_bytes
                        poppler_path = r'C:\Users\rahul\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin'
                        if os.path.exists(poppler_path):
                            images = convert_from_bytes(file_bytes, poppler_path=poppler_path)
                        else:
                            images = convert_from_bytes(file_bytes)
                            
                        ocr_text = ""
                        for img in images:
                            ocr_text += pytesseract.image_to_string(img) + "\n"
                        report_text = ocr_text.strip()
                    except Exception as ocr_e:
                        print(f"PDF OCR failed: {ocr_e}")
                        
            except Exception as e:
                return jsonify({"error": f"Failed to read PDF file: {str(e)}"}), 400
                
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
            try:
                import pytesseract
                import os
                tess_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                if os.path.exists(tess_path):
                    pytesseract.pytesseract.tesseract_cmd = tess_path
                    
                from PIL import Image
                import io
                image = Image.open(io.BytesIO(file_bytes))
                report_text = pytesseract.image_to_string(image).strip()
            except Exception as e:
                return jsonify({"error": f"Failed to run OCR on image: {str(e)}"}), 400
                
        else:
            report_text = file_bytes.decode("utf-8", errors="ignore").strip()

    if not report_text:
        return jsonify({"error": "Please paste or upload a medical report."}), 400
    
    if not city:
        return jsonify({"error": "Please provide a city to find doctors and hospitals."}), 400

    try:
        analysis = call_ai(report_text, city, language=language)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    if "NOT_A_MEDICAL_REPORT" in analysis:
        return jsonify({"error": "The provided document does not appear to be a valid medical report. Please upload a medical document."}), 400

    specialist, severity = parse_ai_output(analysis)
    
    history = load_history()
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "report_excerpt": report_text[:180],
        "analysis": analysis,
        "specialist": specialist,
        "severity": severity,
        "city": city,
        "language": language,
    }
    history.insert(0, entry)
    save_history(history[:30])

    return jsonify(
        {
            "analysis": analysis,
            "specialist": specialist,
            "severity": severity,
            "city": city,
        }
    )


@app.route("/api/history", methods=["GET"])
def history_api():
    return jsonify({"history": load_history()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
