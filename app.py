# app.py
import streamlit as st
from firebase_config import get_firestore_client
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="MedTree",
    page_icon="🏥",
    layout="centered"
)

# Initialize session state variables if they don't exist
if 'doctor_logged_in' not in st.session_state:
    st.session_state.doctor_logged_in = False
if 'patient_logged_in' not in st.session_state:
    st.session_state.patient_logged_in = False

# --- Firebase Connection ---
db = get_firestore_client()

# --- UI ---
st.title("🏥 MedTree")
st.write("Your personal health record companion.")

# --- Login Logic ---
login_tab1, login_tab2 = st.tabs(["Doctor Login", "Patient Login"])

with login_tab1:
    st.header("Doctor Portal")
    with st.form("doctor_login_form"):
        doctor_id = st.text_input("Enter your Doctor ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if not doctor_id or not password:
                st.error("Doctor ID and Password cannot be empty.")
            else:
                doctor_ref = db.collection("doctors").document(doctor_id).get()
                if doctor_ref.exists:
                    doctor_data = doctor_ref.to_dict()
                    # Check if the password matches
                    if doctor_data.get('password') == password:
                        st.session_state.doctor_logged_in = True
                        st.session_state.doctor_id = doctor_id
                        st.session_state.doctor_name = doctor_data.get('name', 'Doctor')
                        st.success("Login Successful!")
                        time.sleep(1) # Brief pause for user to see message
                        st.switch_page("pages/1_Doctor_Dashboard.py")
                    else:
                        st.error("Invalid Doctor ID or Password. Please try again.")
                else:
                    st.error("Invalid Doctor ID or Password. Please try again.")

with login_tab2:
    st.header("Patient Portal")
    with st.form("patient_login_form"):
        patient_id = st.text_input("Enter your Patient ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if not patient_id or not password:
                st.error("Patient ID and Password cannot be empty.")
            else:
                patient_ref = db.collection("patients").document(patient_id).get()
                if patient_ref.exists:
                    patient_data = patient_ref.to_dict()
                    # Check if the password matches
                    if patient_data.get('password') == password:
                        st.session_state.patient_logged_in = True
                        st.session_state.patient_id = patient_id
                        st.session_state.patient_name = patient_data.get('Name', 'Patient')
                        st.success("Login Successful!")
                        time.sleep