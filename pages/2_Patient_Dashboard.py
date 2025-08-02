# pages/2_Patient_Dashboard.py
import streamlit as st
from firebase_config import get_firestore_client
import pandas as pd
from datetime import datetime

hide_sidebar_style = """
    <style>
        [data-testid="stSidebar"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)

# --- Page Configuration and Authentication ---
st.set_page_config(page_title="Patient Dashboard", page_icon="👤", layout="wide")

if not st.session_state.get('patient_logged_in'):
    st.error("You must be logged in to view this page.")
    st.stop()

st.title(f"👤 Welcome, {st.session_state.get('patient_name', 'Patient')}!")
st.sidebar.button("Logout", on_click=lambda: st.switch_page("app.py"))

# --- Firebase Connection ---
db = get_firestore_client()
patient_id = st.session_state.patient_id

# --- Main Page Layout ---
tab1, tab2 = st.tabs(["View Prescriptions & Records", "My Medical Diary"])

# --- TAB 1: View Prescriptions & Records ---
with tab1:
    st.header("Your Medical Records")

    # Display Prescriptions
    st.subheader("💊 Current and Past Prescriptions")
    prescriptions_ref = db.collection("prescriptions").where("patient_id", "==", patient_id).order_by("timestamp", direction="DESCENDING").stream()
    prescriptions = [doc.to_dict() for doc in prescriptions_ref]
    if prescriptions:
        df = pd.DataFrame(prescriptions)
        df['timing'] = df['timing'].apply(lambda x: ', '.join(x))
        st.dataframe(df[['medication_name', 'condition', 'duration', 'timing']], use_container_width=True)
    else:
        st.info("No prescriptions found on your record.")

    # Display Allergies
    st.subheader("🤧 Recorded Allergies and Conditions")
    allergies_ref = db.collection("allergies_and_conditions").where("patient_id", "==", patient_id).stream()
    allergies = [doc.to_dict()['description'] for doc in allergies_ref]
    if allergies:
        for allergy in allergies:
            st.info(allergy)
    else:
        st.info("No allergies or conditions are on record.")

    # Display Scans
    st.subheader("📷 Your Medical Scans")
    scans_ref = db.collection("scans").where("patient_id", "==", patient_id).stream()
    scans = [doc.to_dict() for doc in scans_ref]
    if scans:
        for scan in scans:
            st.markdown(f"- **{scan['body_part']}**: [View Scan File]({scan['file_url']})")
    else:
        st.info("No scans found on your record.")


# --- TAB 2: Medical Diary ---
with tab2:
    st.header("My Medical Diary")
    st.write("Keep track of your symptoms, feelings, or health progress.")

    # Form to add a new diary entry
    with st.form("diary_form", clear_on_submit=True):
        entry_date = st.date_input("Entry Date", value=datetime.today())
        diary_note = st.text_area("How are you feeling today?")
        submitted = st.form_submit_button("Save Entry")

        if submitted and diary_note:
            db.collection("medicaldiary").add({
                "patient_id": patient_id,
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "note": diary_note,
                "timestamp": datetime.now()
            })
            st.success("Your diary entry has been saved!")

    # Display past diary entries
    st.subheader("Past Entries")
    diary_ref = db.collection("medicaldiary").where("patient_id", "==", patient_id).order_by("timestamp", direction="DESCENDING").stream()
    diary_entries = [doc.to_dict() for doc in diary_ref]

    if diary_entries:
        for entry in diary_entries:
            with st.expander(f"**{entry['entry_date']}**"):
                st.write(entry['note'])
    else:
        st.info("You have no diary entries yet. Add one above!")