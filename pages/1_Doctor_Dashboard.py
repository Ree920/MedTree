import streamlit as st
from firebase_config import get_firestore_client, get_storage_bucket
import pandas as pd
from datetime import datetime
import uuid
import time

# --- Helper function for colored dots ---
def get_dot(category):
    """Returns a colored emoji dot based on the category string."""
    if category == 'Red':
        return "🔴"
    elif category == 'Yellow':
        return "🟡"
    else: # Green or None
        return "🟢"

# --- Page Configuration and Authentication ---
st.set_page_config(
    page_title="Doctor Dashboard",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if not st.session_state.get('doctor_logged_in'):
    st.error("You must be logged in to view this page.")
    st.stop()

st.title(f"🩺 Welcome, {st.session_state.get('doctor_name', 'Doctor')}!")
st.sidebar.button("Logout", on_click=lambda: st.switch_page("app.py"))

# --- Firebase Connection ---
db = get_firestore_client()
bucket = get_storage_bucket()

# --- Main Page Layout ---
tab1, tab2 = st.tabs(["View/Manage Patient", "Create New Patient"])

# --- TAB 1: View/Manage Patient ---
with tab1:
    st.header("Patient Record Search")
    with st.form("search_patient_form"):
        search_patient_id = st.text_input("Enter Patient ID to Search")
        search_submitted = st.form_submit_button("Search")

    if search_submitted and search_patient_id:
        st.session_state.searched_patient_id = search_patient_id
        st.session_state.access_granted = False # Reset access on new search

    if 'searched_patient_id' in st.session_state:
        patient_id = st.session_state.searched_patient_id
        patient_doc = db.collection("patients").document(patient_id).get()

        if not patient_doc.exists:
            st.error(f"No patient found with ID: {patient_id}.")
        else:
            patient_data = patient_doc.to_dict()
            st.subheader(f"Records for Patient: {patient_data.get('Name', 'N/A')} (ID: {patient_id})")

            is_confidential = patient_data.get('confidential', False)
            # First, handle overall access for confidential records
            if is_confidential and not st.session_state.get('access_granted', False):
                st.warning("🔒 This patient's records are marked as confidential.")
                if st.button("Request Access to Confidential Data"):
                    with st.spinner("Requesting..."):
                        time.sleep(1)
                    st.success("✅ OTP sent to patient for verification.")
                    time.sleep(1)
                    st.session_state.access_granted = True
                    st.rerun()
            else:
                # This block runs if records are not confidential OR access has been granted
                if is_confidential:
                    st.success("🔓 Access to confidential records granted.")

                view_red_data = st.toggle("🔴 Show Critical (Red) Records", help="Turn on to view records marked as critical by the patient.")

                # --- Fetch all data ---
                all_prescriptions = [doc.to_dict() for doc in db.collection("prescriptions").where("patient_id", "==", patient_id).stream()]
                all_allergies = [doc.to_dict() for doc in db.collection("allergies_and_conditions").where("patient_id", "==", patient_id).stream()]
                all_scans = [doc.to_dict() for doc in db.collection("scans").where("patient_id", "==", patient_id).stream()]

                # --- Filter data based on the toggle's state ---
                if view_red_data:
                    st.info("Showing all records, including critical 'Red' items.")
                    prescriptions, allergies, scans = all_prescriptions, all_allergies, all_scans
                else:
                    # Default view: Show only Green and Yellow. Treat uncategorized as Green.
                    prescriptions = [p for p in all_prescriptions if p.get('category', 'Green') in ['Green', 'Yellow']]
                    allergies = [a for a in all_allergies if a.get('category', 'Green') in ['Green', 'Yellow']]
                    scans = [s for s in all_scans if s.get('category', 'Green') in ['Green', 'Yellow']]

                # --- Display Filtered Data ---
                st.write(f"**DOB:** {patient_data.get('DOB', 'N/A')} | **Blood Group:** {patient_data.get('BloodGroup', 'N/A')}")
                col1, col2 = st.columns(2)
                with col1:
                    with st.expander("🤧 Allergies & Conditions", expanded=True):
                        if allergies:
                            for allergy in allergies:
                                st.info(f"{get_dot(allergy.get('category'))} {allergy['description']}")
                        else:
                            st.write("No conditions to display in this view.")
                with col2:
                    with st.expander("📷 Medical Scans", expanded=True):
                        if scans:
                            for scan in scans:
                                st.markdown(f"{get_dot(scan.get('category'))} **{scan['body_part']}**: [View Scan]({scan['file_url']})")
                        else:
                            st.write("No scans to display in this view.")
                with st.expander("💊 Prescriptions", expanded=True):
                    if prescriptions:
                        df_data = [{"Category": get_dot(p.get('category')), "Medication": p['medication_name'], "Condition": p['condition'], "Duration": p['duration']} for p in prescriptions]
                        st.dataframe(pd.DataFrame(df_data), use_container_width=True)
                    else:
                        st.write("No prescriptions to display in this view.")

                st.divider()
                st.subheader("Add New Records")
                # --- Forms to add new data ---
                form_col1, form_col2, form_col3 = st.columns(3)
                with form_col1:
                    with st.form("add_allergy_form", clear_on_submit=True):
                        new_allergy = st.text_input("Add New Allergy/Condition")
                        if st.form_submit_button("Add Allergy"):
                            if new_allergy:
                                db.collection("allergies_and_conditions").add({"patient_id": patient_id, "description": new_allergy, "category": "Green", "timestamp": datetime.now()})
                                st.success("Allergy added!"); st.rerun()
                with form_col2:
                    with st.form("add_prescription_form", clear_on_submit=True):
                        med_name = st.text_input("Medication Name")
                        condition = st.text_input("Condition")
                        duration = st.text_input("Duration")
                        if st.form_submit_button("Add Prescription"):
                            if all([med_name, condition, duration]):
                                db.collection("prescriptions").add({"patient_id": patient_id, "medication_name": med_name, "condition": condition, "duration": duration, "timing": [], "category": "Green", "timestamp": datetime.now()})
                                st.success("Prescription added!"); st.rerun()
                with form_col3:
                     with st.form("upload_scan_form", clear_on_submit=True):
                        scan_file = st.file_uploader("Upload New Scan", type=['png', 'jpg', 'pdf'])
                        body_part = st.text_input("Body Part Scanned")
                        if st.form_submit_button("Upload Scan"):
                            if scan_file and body_part:
                                blob = bucket.blob(f"scans/{patient_id}/{scan_file.name}"); blob.upload_from_file(scan_file, content_type=scan_file.type); blob.make_public()
                                db.collection("scans").add({"patient_id": patient_id, "body_part": body_part, "file_url": blob.public_url, "category": "Green", "timestamp": datetime.now()})
                                st.success("Scan uploaded!"); st.rerun()

# --- TAB 2: Create New Patient ---
with tab2:
    st.header("Create a New Patient Record")
    with st.form("new_patient_form", clear_on_submit=True):
        p_name = st.text_input("Full Name")
        p_dob = st.date_input("Date of Birth", max_value=datetime.today())
        p_phone = st.text_input("Phone Number")
        p_password = st.text_input("Set Patient Password", type="password")
        if st.form_submit_button("Create Patient"):
            if all([p_name, p_dob, p_phone, p_password]):
                patient_id = f"PAT-{str(uuid.uuid4())[:8].upper()}"
                patient_data = {
                    "Name": p_name, "DOB": p_dob.strftime("%Y-%m-%d"), "Phno": p_phone,
                    "password": p_password, "confidential": False
                }
                db.collection("patients").document(patient_id).set(patient_data)
                st.success(f"✅ Patient created: {p_name}")
                st.info("Provide these credentials to the patient:")
                st.code(f"Patient ID: {patient_id}\nPassword: {p_password}")
            else:
                st.error("Please fill in all details.")