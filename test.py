import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase app (only once)
cred = credentials.Certificate("path_to_your_service_account.json")  # e.g., 'firebase_key.json'
firebase_admin.initialize_app(cred)

db = firestore.client()

# Dummy doctor
db.collection("doctors").document("doc001").set({
    "name": "Dr. John Smith",
    "password": "pass123",
    "specialization": "Cardiology"
})