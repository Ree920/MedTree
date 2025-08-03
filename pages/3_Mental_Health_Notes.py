# pages/3_Mental_Health_Notes.py
import streamlit as st
from firebase_config import get_firestore_client
from datetime import datetime
import azure.cognitiveservices.speech as speechsdk
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import pydub
import io
import logging

# --- Basic Configuration ---
# Suppress excessive logging from pydub
logging.basicConfig()
logging.getLogger("pydub").setLevel(logging.WARNING)

# --- Page Configuration and Authentication ---
st.set_page_config(page_title="Mental Health Notes", page_icon="🧠", layout="wide")

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

# --- Azure and Firebase Setup ---

SPEECH_KEY = st.secrets["azure"]["speech_key"]
SPEECH_REGION = st.secrets["azure"]["speech_region"]
speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)


db = get_firestore_client()
patient_id = st.session_state.patient_id

# --- WebRTC Audio Processor for Azure ---
class AzureAudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_frames = []

    def recv(self, frame):
        # Append audio frames from the browser to an in-memory buffer
        self.audio_frames.append(frame)
        return frame

    def on_ended(self):
        # This method is called when the user stops the recording
        if not self.audio_frames:
            return

        sound = pydub.AudioSegment.empty()
        for frame in self.audio_frames:
            sound += frame

        # Ignore very short, likely accidental recordings
        if sound.duration_seconds < 0.5:
            self.audio_frames.clear()
            return

        # Re-sample audio to the format Azure Speech SDK requires (16kHz, 16-bit, mono)
        sound = sound.set_frame_rate(16000).set_sample_width(2).set_channels(1)
        
        # Export audio to an in-memory WAV byte stream
        wav_buffer = io.BytesIO()
        sound.export(wav_buffer, format="wav")
        wav_bytes = wav_buffer.getvalue()

        # Set up a push stream for the Azure SDK
        stream = speechsdk.audio.PushAudioInputStream()
        stream.write(wav_bytes)
        stream.close()

        # Recognize speech and store the result in session_state
        audio_config = speechsdk.audio.AudioConfig(stream=stream)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        result = speech_recognizer.recognize_once_async().get()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            st.session_state.transcribed_text = result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            st.session_state.transcribed_text = "Error: Speech could not be recognized."
        elif result.reason == speechsdk.ResultReason.Canceled:
            st.session_state.transcribed_text = f"Error: Speech recognition canceled. Reason: {result.cancellation_details.reason}"

        self.audio_frames.clear()

# --- Session State Initialization ---
if "transcribed_text" not in st.session_state:
    st.session_state.transcribed_text = ""
if "note_content" not in st.session_state:
    st.session_state.note_content = ""

# --- Main Page UI ---
st.title("🧠 My Private Mental Health Notes")
st.caption("This is a safe and private space for your thoughts. ")
st.markdown("---")

# If a new transcription is available, update the text area content
if st.session_state.transcribed_text:
    st.session_state.note_content = st.session_state.transcribed_text
    st.session_state.transcribed_text = "" # Clear after copying to prevent re-copying

# --- Voice Note Section ---
st.subheader("Add a Voice Note")
st.write("**Important:** You must grant microphone access when your browser prompts you.")

from streamlit_webrtc import webrtc_streamer, WebRtcMode
# The webrtc_streamer component that captures audio
st.write("DEBUG: logged in?", st.session_state.get("patient_logged_in"))
webrtc_ctx = webrtc_streamer(
    key="speech-to-text-recorder",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AzureAudioProcessor,
    media_stream_constraints={"video": False, "audio": True},
)

# Provide clear UI feedback based on the component's state
if webrtc_ctx.state.playing:
    st.info("🎙️ Recording in progress... Click STOP to finish.")
else:
    st.info("▶️ The recorder is ready. Click START to begin.")

st.markdown("---")

# --- Form to Add/Edit and Save a New Note ---
st.subheader("Your Note")
with st.form("mental_health_note_form"):
    note_content_input = st.text_area(
        "Your transcribed text will appear here. You can also type or edit directly.",
        value=st.session_state.note_content,
        height=200,
        key="text_area_content"
    )
    submitted = st.form_submit_button("Save Note to Diary")

    if submitted and note_content_input:
        db.collection("mental_health_notes").add({
            "patient_id": patient_id,
            "note": note_content_input,
            "timestamp": datetime.now()
        })
        st.success("Your note has been saved successfully!")
        st.session_state.note_content = "" # Clear content after saving
        st.rerun()

# --- Display Past Notes ---
st.header("Your Past Entries")
try:
    notes_ref = db.collection("mental_health_notes").where("patient_id", "==", patient_id).order_by("timestamp", direction="DESCENDING").stream()
    notes_entries = list(notes_ref)

    if notes_entries:
        for note_doc in notes_entries:
            note = note_doc.to_dict()
            entry_date = note['timestamp'].strftime("%B %d, %Y at %I:%M %p")
            with st.expander(f"**Note from: {entry_date}**"):
                st.write(note['note'])
    else:
        st.info("You haven't saved any notes yet. Use the form above to get started.")
except Exception as e:
    st.error(f"Failed to load notes: {e}")