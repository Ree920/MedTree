import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime


try:
    # Initialize the app with a service account, granting admin privileges
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    print("Firebase App initialized successfully.")
    
except Exception as e:
    print(f"Error initializing Firebase App: {e}")
    exit()


# Get a client instance for Firestore
db = firestore.client()

# --- Database Functions ---

def add_personal_details(user_id, name, age, dob, phone_no, address):
    """
    Adds or updates a user's personal details in the 'personal_details' collection.
    The document ID is the same as the user_id for easy retrieval.
    """
    try:
        doc_ref = db.collection('personal_details').document(user_id)
        doc_ref.set({
            'user_id': user_id,
            'name': name,
            'age': age,
            'date_of_birth': dob,
            'phone_number': phone_no,
            'address': address
        })
        print(f"Successfully added personal details for user: {user_id}")
        return doc_ref
    except Exception as e:
        print(f"Error adding personal details: {e}")
        return None

def add_vitals(user_id, blood_group, weight, medical_conditions, allergies):
    """
    Adds or updates a user's vitals in the 'vitals' collection.
    The document ID is the same as the user_id.
    """
    try:
        doc_ref = db.collection('vitals').document(user_id)
        doc_ref.set({
            'blood_group': blood_group,
            'weight_kg': weight,
            'medical_conditions': medical_conditions, # This can be a list of strings
            'allergies': allergies # This can be a list of strings
        })
        print(f"Successfully added vitals for user: {user_id}")
        return doc_ref
    except Exception as e:
        print(f"Error adding vitals: {e}")
        return None

def add_prescription(user_id, condition, medicine, duration, remarks, dosage):
    """
    Adds a new prescription to the 'prescriptions' subcollection for a user.
    Returns a reference to the newly created prescription document.
    """
    try:
        # Prescriptions are stored in a subcollection under the user's personal details
        user_ref = db.collection('personal_details').document(user_id)
        prescriptions_ref = user_ref.collection('prescriptions')

        # Add a new document with an auto-generated ID
        update_time, doc_ref = prescriptions_ref.add({
            'condition': condition,
            'medicine': medicine,
            'duration_days': duration,
            'remarks': remarks,
            'dosage': dosage,
            'date_issued': datetime.datetime.now(datetime.timezone.utc)
        })
        print(f"Successfully added prescription with ID: {doc_ref.id}")
        return doc_ref # Return the DocumentReference object
    except Exception as e:
        print(f"Error adding prescription: {e}")
        return None

def add_treatment(user_id, start_date, end_date, condition, prescription_ref, scans_or_uploads):
    """
    Adds a new treatment record to the 'treatments' subcollection for a user.
    It links to a prescription via a document reference.
    """
    try:
        # Treatments are stored in a subcollection under the user's personal details
        user_ref = db.collection('personal_details').document(user_id)
        treatments_ref = user_ref.collection('treatments')

        # Add a new document with an auto-generated ID
        update_time, doc_ref = treatments_ref.add({
            'start_date': start_date,
            'end_date': end_date,
            'condition': condition,
            'prescription': prescription_ref, # Storing the reference to the prescription
            'scan_urls': scans_or_uploads, # This would be a list of URLs to uploaded files
            'date_recorded': datetime.datetime.now(datetime.timezone.utc)
        })
        print(f"Successfully added treatment with ID: {doc_ref.id}")
        return doc_ref
    except Exception as e:
        print(f"Error adding treatment: {e}")
        return None

# --- Main Execution Block ---
if __name__ == "__main__":
    print("\n--- Running Firestore Health Record Seeder ---\n")

    # A sample user ID. In a real application, this would come from your
    # authentication system (e.g., Firebase Authentication).
    sample_user_id = "user_jane_doe_001"

    # 1. Add Personal Details
    add_personal_details(
        user_id=sample_user_id,
        name="Jane Doe",
        age=34,
        dob="1990-05-15",
        phone_no="123-456-7890",
        address="123 Health St, Wellness City, MedState 12345"
    )

    # 2. Add Vitals
    add_vitals(
        user_id=sample_user_id,
        blood_group="O+",
        weight=68.5,
        medical_conditions=["Hypertension", "Asthma"],
        allergies=["Pollen", "Peanuts"]
    )

    # 3. Add a Prescription for a specific condition
    # This function returns a reference that we can use in the treatment record.
    condition_for_prescription = "Seasonal Allergies"
    prescription_reference = add_prescription(
        user_id=sample_user_id,
        condition=condition_for_prescription,
        medicine="Antihistamine XYZ",
        duration=30,
        remarks="Take one tablet daily after breakfast.",
        dosage="10mg"
    )

    # 4. Add a Treatment, linking the prescription we just created
    if prescription_reference:
        add_treatment(
            user_id=sample_user_id,
            start_date="2024-07-01",
            end_date="2024-07-30",
            condition=condition_for_prescription,
            prescription_ref=prescription_reference, # Here we link the documents
            scans_or_uploads=[
                "https://storage.googleapis.com/your-bucket/scans/scan_01.jpg",
                "https://storage.googleapis.com/your-bucket/reports/report_a1.pdf"
            ]
        )
    else:
        print("\nSkipping treatment creation because prescription failed.")

    print("\n--- Seeder script finished ---\n")

