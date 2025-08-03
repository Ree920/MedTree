# pages/2_Patient_Dashboard.py
import streamlit as st
from firebase_config import get_firestore_client
import pandas as pd
from datetime import datetime
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore

# Imports for Voice-to-Text Feature
import logging
import io
import pydub
import azure.cognitiveservices.speech as speechsdk
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import sys
import os
import queue # Import the queue library
from dotenv import load_dotenv
load_dotenv()  

# --- Helper functions ---
def get_dot(category):
    """Returns a colored emoji dot based on the category string."""
    if category == 'Red': return "🔴"
    elif category == 'Yellow': return "🟡"
    else: return "🟢"

def update_category(collection, doc_id, key):
    """Callback function to update a document's category in Firestore."""
    new_category = st.session_state.get(key)
    if new_category:
        db.collection(collection).document(doc_id).update({"category": new_category})
        st.toast("Category updated!", icon="✅")

# --- Page Configuration and Authentication ---
st.set_page_config(
    page_title="Patient Dashboard",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide the sidebar completely
st.markdown("""
<style>
    .css-1d391kg {display: none}
    .css-1rs6os {display: none}
    .css-17eq0hr {display: none}
    [data-testid="stSidebar"] {display: none}
    [data-testid="collapsedControl"] {display: none}
    .css-1lcbmhc {margin-left: 0rem}
    .css-1outpf7 {margin-left: 0rem}
    section[data-testid="stSidebar"] {display: none !important}
</style>
""", unsafe_allow_html=True)

if not st.session_state.get('patient_logged_in'):
    st.error("You must be logged in to view this page.")
    st.stop()

st.title(f"👤 Welcome, {st.session_state.get('patient_name', 'Patient')}!")
st.sidebar.button("Logout", on_click=lambda: st.switch_page("app.py"))

# --- Firebase Connection ---
db = get_firestore_client()
patient_id = st.session_state.patient_id
patient_name = st.session_state.patient_name
patient_ref = db.collection("patients").document(patient_id)

# --- Initialize Session State ---
if 'viewing_group_id' not in st.session_state:
    st.session_state.viewing_group_id = None
if "note_content" not in st.session_state:
    st.session_state.note_content = ""

# --- Main Page Layout ---
tab1, tab2, tab3 = st.tabs(["Medical Records 🩺", "Private Voice Notes 🧠", "Family Tree Group 🌳"])

# =================================================================================================
# --- TAB 1: Medical Records ---
# =================================================================================================
with tab1:
    st.header("Privacy & Record Categorization")
    st.caption("Mark your entire record as confidential or set the priority for each item below.")
    # --- Settings ---
    try:
        patient_data = patient_ref.get().to_dict()
        current_confidential_status = patient_data.get('confidential', False)
    except Exception as e:
        st.error(f"Could not load your data: {e}")
        st.stop()

    new_status = st.toggle("🔒 Mark all my records as Confidential", value=current_confidential_status)
    if new_status != current_confidential_status:
        patient_ref.update({"confidential": new_status}); st.toast("Privacy setting updated!")
    st.divider()

    st.header("Your Medical Records")
    CAT_OPTIONS = ["Green", "Yellow", "Red"]

    # Prescriptions Table
    st.subheader("💊 Prescriptions")
    prescriptions = [{"id": doc.id, **doc.to_dict()} for doc in db.collection("prescriptions").where(filter=FieldFilter("patient_id", "==", patient_id)).stream()]
    if prescriptions:
        h_cols = st.columns([3,3,2,1,2]); h_cols[0].markdown("**Medication**"); h_cols[1].markdown("**Condition**"); h_cols[2].markdown("**Duration**"); h_cols[3].markdown("**Status**"); h_cols[4].markdown("**Set Category**"); st.markdown("---")
        for p in prescriptions:
            cat = p.get('category', 'Green')
            r_cols = st.columns([3,3,2,1,2]); r_cols[0].write(p.get('medication_name')); r_cols[1].write(p.get('condition')); r_cols[2].write(p.get('duration')); r_cols[3].write(get_dot(cat)); r_cols[4].selectbox("Set", CAT_OPTIONS, index=CAT_OPTIONS.index(cat), key=f"p_{p['id']}", on_change=update_category, args=("prescriptions", p['id'], f"p_{p['id']}"), label_visibility="collapsed")
    else: st.info("No prescriptions found.")

    # Allergies Table
    st.subheader("🤧 Health History")
    allergies = [{"id": doc.id, **doc.to_dict()} for doc in db.collection("allergies_and_conditions").where(filter=FieldFilter("patient_id", "==", patient_id)).stream()]
    if allergies:
        h_cols = st.columns([6,1,2]); h_cols[0].markdown("**Description**"); h_cols[1].markdown("**Status**"); h_cols[2].markdown("**Set Category**"); st.markdown("---")
        for a in allergies:
            cat = a.get('category', 'Green')
            r_cols = st.columns([6,1,2]); r_cols[0].info(a.get('description')); r_cols[1].write(get_dot(cat)); r_cols[2].selectbox("Set", CAT_OPTIONS, index=CAT_OPTIONS.index(cat), key=f"a_{a['id']}", on_change=update_category, args=("allergies_and_conditions", a['id'], f"a_{a['id']}"), label_visibility="collapsed")
    else: st.info("No allergies recorded.")

    # Scans Table
    st.subheader("📷 Medical Scans")
    scans = [{"id": doc.id, **doc.to_dict()} for doc in db.collection("scans").where(filter=FieldFilter("patient_id", "==", patient_id)).stream()]
    if scans:
        h_cols = st.columns([5,2,1,2]); h_cols[0].markdown("**Body Part**"); h_cols[1].markdown("**View File**"); h_cols[2].markdown("**Status**"); h_cols[3].markdown("**Set Category**"); st.markdown("---")
        for s in scans:
            cat = s.get('category', 'Green')
            r_cols = st.columns([5,2,1,2]); r_cols[0].write(s.get('body_part')); r_cols[1].markdown(f"[Link to Scan]({s.get('file_url')})"); r_cols[2].write(get_dot(cat)); r_cols[3].selectbox("Set", CAT_OPTIONS, index=CAT_OPTIONS.index(cat), key=f"s_{s['id']}", on_change=update_category, args=("scans", s['id'], f"s_{s['id']}"), label_visibility="collapsed")
    else: st.info("No scans found.")

# =================================================================================================
# --- TAB 2: Private Voice Notes ---
# =================================================================================================
with tab2:
    # --- Basic Configuration ---
    logging.getLogger("pydub").setLevel(logging.WARNING)

    # Use st.cache_resource to create the speech_config object only once.
    @st.cache_resource
    def get_speech_config():
        try:
            speech_key = os.environ.get('SPEECH_KEY')
            speech_endpoint = os.environ.get('SPEECH_ENDPOINT')
            if not all([speech_key, speech_endpoint]):
                return None
            config = speechsdk.SpeechConfig(subscription=speech_key, endpoint=speech_endpoint)
            config.speech_recognition_language = "en-US"
            print("✅ Successfully configured Azure Speech Service client. (This will only run once)")
            return config
        except Exception as e:
            print(f"❌ Error during Azure Speech Service client initialization: {e}", file=sys.stderr)
            return None

    speech_config = get_speech_config()

    if not speech_config:
        st.error("Audio transcription is disabled. Please set the environment variables: `SPEECH_KEY` and `SPEECH_ENDPOINT`.")
    else:
        # --- WebRTC Audio Processor with Queue for reliable communication ---
        class AzureSpeechSDKProcessor(AudioProcessorBase):
            def __init__(self, result_queue):
                self.audio_frames = []
                self.is_processing = False
                self.result_queue = result_queue # To send results back to the main thread

            def recv_queued(self, frames):
                self.audio_frames.extend(frames)

            def on_ended(self):
                if self.is_processing or not self.audio_frames:
                    return

                self.is_processing = True
                sound = pydub.AudioSegment.empty()
                for frame in self.audio_frames:
                    sound += frame
                self.audio_frames.clear()

                if sound.duration_seconds < 0.5:
                    self.is_processing = False
                    return

                try:
                    sound = sound.set_frame_rate(16000).set_sample_width(2).set_channels(1)
                    wav_buffer = io.BytesIO()
                    sound.export(wav_buffer, format="wav")
                    stream = speechsdk.audio.PushAudioInputStream()
                    stream.write(wav_buffer.getvalue())
                    stream.close()

                    audio_config = speechsdk.audio.AudioConfig(stream=stream)
                    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
                    result = speech_recognizer.recognize_once_async().get()

                    final_text = ""
                    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                        final_text = result.text
                    elif result.reason == speechsdk.ResultReason.NoMatch:
                        final_text = "Error: Speech could not be recognized."
                    elif result.reason == speechsdk.ResultReason.Canceled:
                        final_text = f"Error: Transcription canceled - {result.cancellation_details.reason}"

                    # Put the result into the queue to safely pass it to the main thread
                    self.result_queue.put(final_text)
                except Exception as e:
                    self.result_queue.put(f"An error occurred during transcription: {e}")
                finally:
                    self.is_processing = False

        # --- Streamlit UI Components ---
        st.header("My Private Voice Notes")
        st.caption("A safe space for your thoughts. These notes are private and not shared with your doctor.")
        st.markdown("---")
        st.subheader("Add a Voice Note")
        st.write("Click START to record your thoughts. Grant microphone access when prompted.")

        # Create the queue before the streamer
        result_queue = queue.Queue()

        webrtc_ctx = webrtc_streamer(
            key="speech-to-text-recorder",
            mode=WebRtcMode.SENDONLY,
            # Pass the queue to the processor factory
            audio_processor_factory=lambda: AzureSpeechSDKProcessor(result_queue=result_queue),
            media_stream_constraints={"video": False, "audio": True},
        )

        if webrtc_ctx.state.playing:
            st.info("🎙️ Recording... Click STOP to finish.")
        else:
            st.info("▶️ Recorder is ready. Click START to begin.")

        # Check the queue for a result when the recorder is not playing
        if not webrtc_ctx.state.playing:
            try:
                # Non-blocking get from the queue
                result = result_queue.get(block=False)
                st.session_state.note_content = result
                st.rerun() # Rerun to update the text_area with the new content
            except queue.Empty:
                pass # No result yet

        st.markdown("---")
        st.subheader("Your Note")

        with st.form("mental_health_note_form"):
            note_content_input = st.text_area(
                "Your transcribed text will appear here. You can also type or edit directly.",
                value=st.session_state.note_content, height=200, key="text_area_content"
            )
            submitted = st.form_submit_button("Save Note to Diary")
            if submitted and note_content_input:
                db.collection("mental_health_notes").add({
                    "patient_id": patient_id,
                    "note": note_content_input,
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
                st.success("Your note has been saved successfully!")
                st.session_state.note_content = "" # Clear the text area after saving
                st.rerun()

        st.header("Your Past Entries")
        notes_ref = db.collection("mental_health_notes").where(filter=FieldFilter("patient_id", "==", patient_id)).order_by("timestamp", direction="DESCENDING").stream()
        notes_list = list(notes_ref)

        if not notes_list:
            st.info("You haven't saved any notes yet.")
        else:
            for note_doc in notes_list:
                note = note_doc.to_dict()
                if 'timestamp' in note and isinstance(note['timestamp'], datetime):
                    entry_date = note['timestamp'].strftime("%B %d, %Y at %I:%M %p")
                    with st.expander(f"**Note from: {entry_date}**"):
                        st.write(note['note'])
                else:
                    st.warning(f"Note with ID {note_doc.id} has a missing or invalid timestamp.")

# =================================================================================================
# --- TAB 3: Family Tree Group ---
# =================================================================================================
# This tab's code remains unchanged.
with tab3:
    st.header("Family Tree Groups")
    st.caption("Create or join groups to share health information with family members.")
    # (Rest of Tab 3 code is here)
    if st.session_state.viewing_group_id:
        group_id = st.session_state.viewing_group_id
        group_doc = db.collection("family_groups").document(group_id).get()
        if group_doc.exists:
            st.subheader(f"Managing Group: *{group_doc.to_dict().get('group_name')}*")
        if st.button("⬅️ Back to All Groups"):
            st.session_state.viewing_group_id = None
            st.rerun()
        with st.expander("Add a new family member to this group"):
            with st.form("add_member_form", clear_on_submit=True):
                new_member_id = st.text_input("New Member's Patient ID")
                relationship = st.text_input("Their relationship to you (e.g., Father, Sister, Son)")
                if st.form_submit_button("Add Member") and new_member_id and relationship:
                    new_member_ref = db.collection("patients").document(new_member_id)
                    new_member_doc = new_member_ref.get()
                    if not new_member_doc.exists:
                        st.error("Patient ID not found.")
                    else:
                        new_member_name = new_member_doc.to_dict().get('Name', 'N/A')
                        db.collection("family_groups").document(group_id).collection("members").document(new_member_id).set({"name": new_member_name,"relationship": relationship,"relative_to_id": patient_id,"added_at": firestore.SERVER_TIMESTAMP})
                        new_member_ref.update({"family_groups": firestore.ArrayUnion([group_id])})
                        st.success(f"Added {new_member_name} to the group!");st.rerun()
        st.subheader("Group Members")
        members_ref = db.collection("family_groups").document(group_id).collection("members").stream()
        members_list = [m.to_dict() for m in members_ref]
        if members_list:
            relative_ids = {m['relative_to_id'] for m in members_list if 'relative_to_id' in m}
            relatives_map = {rid: db.collection('patients').document(rid).get().to_dict().get('Name', 'Unknown') for rid in relative_ids}
            h_cols = st.columns([2,2,2]); h_cols[0].markdown("**Name**"); h_cols[1].markdown("**Relationship**"); h_cols[2].markdown("**Relative To**")
            for member in members_list:
                r_cols = st.columns([2,2,2]); r_cols[0].write(member.get('name')); r_cols[1].write(member.get('relationship')); r_cols[2].write(relatives_map.get(member.get('relative_to_id'), "N/A"))
        else:
            st.info("This group has no members yet. Add one using the form above.")
    else:
        with st.expander("Create a New Family Group"):
            with st.form("new_group_form", clear_on_submit=True):
                group_name = st.text_input("New Group Name (e.g., Paternal Side)")
                if st.form_submit_button("Create Group") and group_name:
                    new_group_ref = db.collection("family_groups").document()
                    batch = db.batch();batch.set(new_group_ref, {"group_name": group_name,"creator_id": patient_id,"created_at": firestore.SERVER_TIMESTAMP});members_subcollection = new_group_ref.collection("members");batch.set(members_subcollection.document(patient_id), {"name": patient_name,"relationship": "Self","relative_to_id": patient_id,"added_at": firestore.SERVER_TIMESTAMP});batch.update(patient_ref, {"family_groups": firestore.ArrayUnion([new_group_ref.id])});batch.commit()
                    st.success(f"Group '{group_name}' created!");st.rerun()
        st.subheader("Your Existing Groups")
        try:
            patient_doc_data = patient_ref.get().to_dict()
            my_group_ids = patient_doc_data.get('family_groups', [])
            if not my_group_ids:
                st.info("You are not part of any groups yet. Create one to get started.")
            else:
                for group_id in my_group_ids:
                    group_doc = db.collection("family_groups").document(group_id).get()
                    if group_doc.exists:
                        g_cols = st.columns([3,1]);g_cols[0].write(f"**{group_doc.to_dict().get('group_name')}**")
                        if g_cols[1].button("View/Manage", key=f"view_{group_id}"):
                            st.session_state.viewing_group_id = group_id
                            st.rerun()
        except Exception as e:
            st.error("Could not load your family groups. Ensure your patient profile has the 'family_groups' field.")