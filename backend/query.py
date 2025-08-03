# backend/query.py
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
import os
import json
import sys

# --- Configuration ---
app = Flask(__name__)
# Load environment variables from a .env file in the same directory
load_dotenv() 

# --- Azure OpenAI Setup ---
try:
    # 🔹 Fetch credentials from environment variables
    AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    # 🔹 Validate that all required variables are set
    if not all([AZURE_API_KEY, AZURE_ENDPOINT, DEPLOYMENT_NAME]):
        raise ValueError("The following environment variables are required: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME")

    # 🔹 Instantiate the Azure OpenAI client
    client = openai.AzureOpenAI(
        api_key=AZURE_API_KEY,
        api_version="2024-12-01-preview",  # Using a recent, stable API version
        azure_endpoint=AZURE_ENDPOINT,
    )
    print("✅ Successfully configured Azure OpenAI client.")

except Exception as e:
    print(f"❌ Error during Azure OpenAI client initialization: {e}", file=sys.stderr)
    sys.exit(1)


# --- Core AI Functions ---
def patient_role(patient_data_str: str) -> str:
    """Generates a concise summary of the patient's data using Azure OpenAI."""
    prompt = f"""
    Analyze the following patient data.
    Focus on current medications, family history, and any ongoing health conditions.
    Present the output as a concise summary using bullet points.

    Patient Data:
    {patient_data_str}
    """
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling Azure OpenAI for patient summary: {e}", file=sys.stderr)
        return "Error: Could not generate patient summary from AI."

def doctor_role(patient_statement: str, procedure: str) -> str:
    """Generates clarifying questions for a doctor based on a patient summary and a procedure."""
    prompt = f"""
    Based on the following patient summary and planned medical procedure, generate a list 
    of 3-5 critical questions a doctor should ask the patient to identify potential risks 
    or complications. The questions should be direct, clear, and focused on patient safety. 
    Only return the questions.

    Planned Procedure: {procedure}

    Patient Summary:
    {patient_statement}
    """
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,  # Slightly higher temperature for more nuanced questions
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling Azure OpenAI for doctor questions: {e}", file=sys.stderr)
        return "Error: Could not generate doctor questions from AI."

def generate(patient_data_json: dict, procedure: str) -> dict:
    """Main function to process patient data and generate AI analysis."""
    try:
        # Convert the JSON to a formatted string for the prompt
        patient_data_str = json.dumps(patient_data_json, indent=2)

        patient_statement = patient_role(patient_data_str)
        if patient_statement.startswith("Error:"):
             return {"status": "error", "message": patient_statement}

        doctor_response = doctor_role(patient_statement, procedure)
        if doctor_response.startswith("Error:"):
             return {"status": "error", "message": doctor_response}

        return {
            "status": "success",
            "patient_statement": patient_statement,
            "doctor_response": doctor_response
        }
    except Exception as e:
        print(f"An error occurred in the generate function: {e}", file=sys.stderr)
        return {"status": "error", "message": str(e)}

# --- API Endpoint ---
@app.route('/api/medical/analyze', methods=['POST'])
def analyze_patient_data():
    """API endpoint to handle patient data analysis requests."""
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        patient_data = data.get('patient_data')
        procedure = data.get('procedure')

        if not patient_data or not procedure:
            return jsonify({"error": "Missing 'patient_data' or 'procedure' in request"}), 400

        result = generate(patient_data, procedure)

        if result.get("status") == "error":
            print(f"API Error: {result.get('message')}", file=sys.stderr)
            return jsonify({"error": "Failed to process the request due to an internal AI service error."}), 500

        return jsonify(result), 200

    except Exception as e:
        print(f"An unexpected error occurred in the API endpoint: {e}", file=sys.stderr)
        return jsonify({"error": "An internal server error occurred."}), 500

# --- Run the App ---
if __name__ == '__main__':
    # Use environment variable for port, defaulting to 5000.
    # Host '0.0.0.0' makes the server accessible on your local network.
    port = int(os.getenv("PORT", 5001))
    app.run(debug=True, host='0.0.0.0', port=port)