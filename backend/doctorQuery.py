from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
import os
import datetime
import sys
import json

# --- Initial Setup ---
load_dotenv()

# This allows importing from a parent directory (e.g., for firebase_config)
# Ensure your project structure matches this.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from firebase_config import get_firestore_client
except ImportError:
    print("Error: Could not import get_firestore_client from firebase_config.")
    print("Please ensure firebase_config.py is in the parent directory.")
    sys.exit(1)


# --- Flask App Initialization ---
app = Flask(__name__)

# --- Service Connections ---
try:
    # 🔹 Firestore Setup
    db = get_firestore_client()

    # 🔹 Azure OpenAI Setup
    AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")

    if not all([AZURE_API_KEY, AZURE_ENDPOINT, DEPLOYMENT_NAME]):
        raise ValueError("One or more Azure OpenAI environment variables are not set.")

    # Use a recent, stable API version
    client = openai.AzureOpenAI(
        api_key=AZURE_API_KEY,
        api_version="2024-02-01",
        azure_endpoint=AZURE_ENDPOINT,
    )
    print("Successfully connected to Firestore and Azure OpenAI.")
except Exception as e:
    print(f"Error during initialization: {e}")
    sys.exit(1)


# --- Firestore Helper Functions ---
# These functions handle interactions with the database.

def add_personal_details(user_id, name, age, dob, phone_no, address):
    """Adds or updates a user's personal details."""
    try:
        doc_ref = db.collection('personal_details').document(user_id)
        doc_ref.set({
            'user_id': user_id, 'name': name, 'age': age,
            'date_of_birth': dob, 'phone_number': phone_no, 'address': address
        })
        print(f"Successfully added/updated personal details for user: {user_id}")
        return doc_ref
    except Exception as e:
        print(f"Error adding personal details for {user_id}: {e}")
        return None

def add_vitals(user_id, blood_group, weight, medical_conditions, allergies):
    """Adds or updates a user's vitals."""
    try:
        doc_ref = db.collection('vitals').document(user_id)
        doc_ref.set({
            'blood_group': blood_group, 'weight_kg': weight,
            'medical_conditions': medical_conditions, 'allergies': allergies
        })
        print(f"Successfully added/updated vitals for user: {user_id}")
        return doc_ref
    except Exception as e:
        print(f"Error adding vitals for {user_id}: {e}")
        return None

def add_prescription(user_id, condition, medicine, duration, remarks, dosage):
    """Adds a new prescription to a user's subcollection."""
    try:
        prescriptions_ref = db.collection('personal_details').document(user_id).collection('prescriptions')
        _update_time, doc_ref = prescriptions_ref.add({
            'condition': condition, 'medicine': medicine, 'duration_days': duration,
            'remarks': remarks, 'dosage': dosage,
            'date_issued': datetime.datetime.now(datetime.timezone.utc)
        })
        print(f"Successfully added prescription {doc_ref.id} for user: {user_id}")
        return doc_ref
    except Exception as e:
        print(f"Error adding prescription for {user_id}: {e}")
        return None

def add_treatment(user_id, start_date, end_date, condition, prescription_ref, scans_or_uploads):
    """Adds a new treatment record, linking to a prescription."""
    try:
        treatments_ref = db.collection('personal_details').document(user_id).collection('treatments')
        _update_time, doc_ref = treatments_ref.add({
            'start_date': start_date, 'end_date': end_date, 'condition': condition,
            'prescription': prescription_ref, 'scan_urls': scans_or_uploads,
            'date_recorded': datetime.datetime.now(datetime.timezone.utc)
        })
        print(f"Successfully added treatment {doc_ref.id} for user: {user_id}")
        return doc_ref
    except Exception as e:
        print(f"Error adding treatment for {user_id}: {e}")
        return None

# --- Azure AI Functions ---
# These functions call the Azure OpenAI service.

def generate_patient_summary(patient_data):
    """Generates a concise summary of patient data using Azure OpenAI."""
    # Convert patient data to a clean JSON string for the prompt
    patient_data_str = json.dumps(patient_data, indent=2)
    prompt = (
        "Analyze the following patient data and generate a concise, bullet-pointed summary "
        "highlighting the most critical information for a doctor's review. Focus on allergies, "
        "chronic medical conditions, and current prescriptions.\n\n"
        f"Patient Data:\n{patient_data_str}"
    )
    
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2 # Lower temperature for more factual, less creative output
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating patient summary from AI: {e}")
        return "Could not generate patient summary due to an AI service error."

def generate_doctor_questions(patient_summary, procedure):
    """Generates relevant questions for a doctor based on the summary and procedure."""
    prompt = (
        "Based on the following patient summary and the planned medical procedure, generate a list "
        "of 3-5 critical questions a doctor should ask the patient to identify potential risks or complications. "
        "The questions should be direct and clear and give only the questions.\n\n"
        f"Patient Summary:\n{patient_summary}\n\n"
        f"Planned Procedure: {procedure}"
    )

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating doctor questions from AI: {e}")
        return "Could not generate doctor questions due to an AI service error."

# --- API Endpoint ---
@app.route('/api/medical/analyze', methods=['POST'])
def analyze_patient_data():
    """
    API endpoint to receive patient data, store it in Firestore,
    and return an AI-generated summary and questions.
    """
    if not request.is_json:
        return jsonify({"error": "Invalid request: Content-Type must be application/json"}), 400

    try:
        data = request.get_json()

        # --- Data Validation ---
        user_id = data.get("user_id")
        procedure = data.get("procedure")
        if not user_id or not procedure:
            return jsonify({"error": "Missing required fields: 'user_id' and 'procedure' are mandatory."}), 400

        # --- Extract Data ---
        personal = data.get("personal_details", {})
        vitals = data.get("vitals", {})
        prescription = data.get("prescription", {})
        treatment = data.get("treatment", {})

        # --- Store Data in Firestore ---
        add_personal_details(user_id, personal.get("name"), personal.get("age"), personal.get("dob"),
                             personal.get("phone_no"), personal.get("address"))

        add_vitals(user_id, vitals.get("blood_group"), vitals.get("weight"),
                   vitals.get("medical_conditions"), vitals.get("allergies"))

        prescription_ref = add_prescription(user_id, prescription.get("condition"), prescription.get("medicine"),
                                            prescription.get("duration"), prescription.get("remarks"), prescription.get("dosage"))

        # Only add treatment if a prescription was successfully created
        if prescription_ref:
            add_treatment(user_id, treatment.get("start_date"), treatment.get("end_date"),
                          treatment.get("condition"), prescription_ref, treatment.get("scans_or_uploads"))

        # --- Generate AI Insights ---
        # Consolidate all data for a comprehensive summary
        full_patient_data = {
            "personal_details": personal,
            "vitals": vitals,
            "current_prescription": prescription
        }
        patient_summary = generate_patient_summary(full_patient_data)
        doctor_questions = generate_doctor_questions(patient_summary, procedure)

        # --- Return Response ---
        return jsonify({
            "status": "success",
            "message": f"Data processed for user {user_id}",
            "patient_summary": patient_summary,
            "doctor_questions": doctor_questions
        }), 200

    except Exception as e:
        print(f"An unexpected error occurred in /api/medical/analyze: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500


if __name__ == '__main__':
    # Runs the Flask app. Use debug=False in a production environment.
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))

