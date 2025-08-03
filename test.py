import firebase_admin
from firebase_admin import credentials, firestore
import json

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# Load JSON data (copy-paste the JSON payload into a file called data.json)
with open("pregnancyData.json", "r") as f:
    data = json.load(f)

# Add data to Firestore (for example in a collection called 'patients')
# You can set a custom document ID or let Firestore auto-generate one
doc_ref = db.collection("pregnancy_details").document("patient_001")
doc_ref.set(data)

print("Data uploaded successfully!")
