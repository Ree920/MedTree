# firebase_config.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage
import json
import os


def init_firebase():
    """Initializes the Firebase app if not already initialized."""
    try:
        # Check if the app is already initialized
        firebase_admin.get_app()
    except ValueError:
        # Try to get credentials from environment variable first (for production)
        firebase_creds = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        
        if firebase_creds:
            # Parse JSON from environment variable
            cred_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(cred_dict)
            project_id = cred_dict['project_id']
        else:
            # Fall back to Streamlit secrets (for local development)
            cred = credentials.Certificate(dict(st.secrets.firebase_service_account))
            project_id = st.secrets.firebase_service_account.project_id
        
        firebase_admin.initialize_app(cred, {
            'storageBucket': f'{project_id}.appspot.com'
        })

def get_firestore_client():
    """Returns a Firestore client instance."""
    init_firebase()
    return firestore.client()

def get_storage_bucket():
    """Returns a Firebase Storage bucket instance."""
    init_firebase()
    return storage.bucket()