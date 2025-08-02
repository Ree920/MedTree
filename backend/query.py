# backend/query.py
from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import json

# --- Configuration ---
app = Flask(__name__)

genai.configure(api_key="AIzaSyBP_BIQpcO6akYyl53xK60WhGsiu9j0y08")
model = genai.GenerativeModel("gemini-1.5-flash")

 


# --- Core AI Functions ---
def patient_role(patient_data_str: str) -> str:
    """Generates a concise summary of the patient's data."""
    prompt = f"""
    Analyze the following patient data. Summarize the key points relevant for a pre-procedure check.
    Focus on allergies, current medications, and any ongoing conditions. Be concise and use bullet points.

    Patient Data:
    {patient_data_str}
    """
    response = model.generate_content(prompt)
    return response.text

def doctor_role(patient_statement: str, procedure: str) -> str:
    """Generates clarifying questions for a doctor based on patient data and a procedure."""
    prompt = f"""
    Based on the following patient summary and the planned procedure, generate a list of 3-5 critical questions a doctor should ask to identify potential complications.

    Planned Procedure: {procedure}
    Patient Summary:
    {patient_statement}
    """
    response = model.generate_content(prompt)
    return response.text

def generate(patient_data_json: dict, procedure: str) -> dict:
    """Main function to process patient data and generate AI analysis."""
    try:
        # Convert the JSON to a string for the prompt
        patient_data_str = json.dumps(patient_data_json, indent=2)

        patient_statement = patient_role(patient_data_str)
        doctor_response = doctor_role(patient_statement, procedure)

        return {
            "status": "success",
            "patient_statement": patient_statement,
            "doctor_response": doctor_response
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- API Endpoint ---
@app.route('/api/medical/analyze', methods=['POST'])
def analyze_patient_data():
    """API endpoint to handle patient data analysis requests."""
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        # The entire patient data bundle is now expected under a single key
        patient_data = data.get('patient_data')
        procedure = data.get('procedure')

        if not patient_data or not procedure:
            return jsonify({"error": "Missing 'patient_data' or 'procedure' in request"}), 400

        result = generate(patient_data, procedure)

        if result.get("status") == "error":
            return jsonify(result), 500

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Run the App ---
if __name__ == '__main__':
    # Runs on localhost, port 5000. Accessible only on your machine.
    app.run(debug=True, host='127.0.0.1', port=5000)