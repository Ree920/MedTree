# pages/1_Doctor_Dashboard.py
import streamlit as st
from firebase_config import get_firestore_client, get_storage_bucket
import pandas as pd
from datetime import datetime
import uuid

hide_sidebar_style = """
    <style>
        [data-testid="stSidebar"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)

# --- Page Configuration and Authentication ---
st.set_page_config(page_title="Doctor Dashboard", page_icon="🩺", layout="wide")

if not st.session_state.get('doctor_logged_in'):
    st.error("You must be logged in to view this page.")
    st.stop()

st.title(f"🩺 Welcome, {st.session_state.get('doctor_name', 'Doctor')}!")
st.sidebar.button("Logout", on_click=lambda: st.switch_page("app.py"))

# --- Firebase Connection ---
db = get_firestore_client()
bucket = get_storage_bucket()

# --- Helper Function to Fetch Patients ---
@st.cache_data(ttl=300)
def get_patients():
    patients_ref = db.collection("patients").stream()
    patients = [{"id": doc.id, **doc.to_dict()} for doc in patients_ref]
    return patients

patients = get_patients()
patient_options = {p['Name']: p['id'] for p in patients} if patients else {}

# --- Main Page Layout ---
tab1, tab2 = st.tabs(["View/Manage Patient", "Create New Patient"])

# --- TAB 1: View/Manage Patient ---
with tab1:
    st.header("Patient Management")
    if not patient_options:
        st.info("No patients found. Please create a new patient record in the next tab.")
    else:
        selected_patient_name = st.selectbox("Select a Patient", options=list(patient_options.keys()))

        if selected_patient_name:
            patient_id = patient_options[selected_patient_name]
            patient_data = db.collection("patients").document(patient_id).get().to_dict()

            st.subheader(f"Records for: {patient_data.get('Name', 'N/A')}")
            st.write(f"**DOB:** {patient_data.get('DOB', 'N/A')} | **Blood Group:** {patient_data.get('BloodGroup', 'N/A')} | **Phone:** {patient_data.get('Phno', 'N/A')}")

            # --- Sections for Allergies, Prescriptions, Scans ---
            col1, col2 = st.columns(2)

            # Allergies & Conditions
            with col1:
                with st.expander("🤧 Allergies & Genetic Conditions", expanded=True):
                    allergies_ref = db.collection("allergies_and_conditions").where("patient_id", "==", patient_id).stream()
                    allergies = [doc.to_dict() for doc in allergies_ref]
                    if allergies:
                        for allergy in allergies:
                            st.info(allergy['description'])
                    else:
                        st.write("No conditions recorded.")

                    with st.form("add_allergy_form", clear_on_submit=True):
                        new_allergy = st.text_input("Add new allergy or condition")
                        if st.form_submit_button("Add Condition"):
                            if new_allergy:
                                db.collection("allergies_and_conditions").add({
                                    "patient_id": patient_id,
                                    "description": new_allergy,
                                    "timestamp": datetime.now()
                                })
                                st.success("Condition added!")
                                st.rerun()

            # Medical Scans
            with col2:
                with st.expander("📷 Medical Scans", expanded=True):
                    scans_ref = db.collection("scans").where("patient_id", "==", patient_id).stream()
                    scans = [doc.to_dict() for doc in scans_ref]
                    if scans:
                        for scan in scans:
                            st.markdown(f"**{scan['body_part']}**: [View Scan]({scan['file_url']})")
                    else:
                        st.write("No scans uploaded.")

                    with st.form("upload_scan_form", clear_on_submit=True):
                        scan_file = st.file_uploader("Upload a new scan", type=['png', 'jpg', 'jpeg', 'pdf'])
                        body_part = st.text_input("Body Part Scanned")
                        if st.form_submit_button("Upload Scan"):
                            if scan_file and body_part:
                                blob = bucket.blob(f"scans/{patient_id}/{scan_file.name}")
                                blob.upload_from_file(scan_file, content_type=scan_file.type)
                                blob.make_public()
                                db.collection("scans").add({
                                    "patient_id": patient_id,
                                    "body_part": body_part,
                                    "file_url": blob.public_url,
                                    "timestamp": datetime.now()
                                })
                                st.success("Scan uploaded!")
                                st.rerun()

            # Prescriptions
            with st.expander("💊 Prescriptions", expanded=True):
                prescriptions_ref = db.collection("prescriptions").where("patient_id", "==", patient_id).stream()
                prescriptions = [doc.to_dict() for doc in prescriptions_ref]
                if prescriptions:
                    df = pd.DataFrame(prescriptions)
                    st.dataframe(df[['medication_name', 'condition', 'timing', 'duration']], use_container_width=True)
                else:
                    st.write("No prescriptions found.")

                with st.form("add_prescription_form", clear_on_submit=True):
                    st.subheader("Add New Prescription")
                    med_name = st.text_input("Medication Name")
                    condition = st.text_input("Condition for Medication")
                    duration = st.text_input("Duration of Course (e.g., '7 days')")
                    timing_cols = st.columns(3)
                    morning = timing_cols[0].checkbox("Morning")
                    evening = timing_cols[1].checkbox("Evening")
                    night = timing_cols[2].checkbox("Night")

                    if st.form_submit_button("Add Prescription"):
                        timing = [t for t, checked in zip(["Morning", "Evening", "Night"], [morning, evening, night]) if checked]
                        if med_name and condition and duration and timing:
                            db.collection("prescriptions").add({
                                "patient_id": patient_id,
                                "medication_name": med_name,
                                "condition": condition,
                                "duration": duration,
                                "timing": timing,
                                "timestamp": datetime.now()
                            })
                            st.success("Prescription added!")
                            st.rerun()

# --- TAB 2: Create New Patient ---
with tab2:
    st.header("Create a New Patient Record")
    with st.form("new_patient_form", clear_on_submit=True):
        st.write("Enter patient details below.")
        p_name = st.text_input("Full Name")
        p_dob = st.date_input("Date of Birth", max_value=datetime.today())
        p_ethnicity = st.text_input("Ethnicity")
        p_blood_group = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
        p_phone = st.text_input("Phone Number")
        p_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        p_password = st.text_input("Set Patient Password", type="password")

        if st.form_submit_button("Create Patient"):
            if all([p_name, p_dob, p_ethnicity, p_blood_group, p_phone, p_gender, p_password]):
                # Generate a unique patient ID
                patient_id = f"PAT-{str(uuid.uuid4())[:6].upper()}"
                patient_data = {
                    "Name": p_name,
                    "DOB": p_dob.strftime("%Y-%m-%d"),
                    "Ethnicity": p_ethnicity,
                    "BloodGroup": p_blood_group,
                    "Phno": p_phone,
                    "Gender": p_gender,
                    "password": p_password  # Store the password
                }
                db.collection("patients").document(patient_id).set(patient_data)
                st.success(f"Successfully created patient: {p_name}")
                st.info(f"Please provide the following credentials to the patient for their login:")
                st.code(f"Patient ID: {patient_id}\nPassword: {p_password}")
                st.cache_data.clear() # Clear cache to refresh patient list
            else:
                st.error("Please fill in all the details, including the password.")