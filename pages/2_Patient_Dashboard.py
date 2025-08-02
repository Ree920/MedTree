# pages/2_Patient_Dashboard.py
import streamlit as st
from firebase_config import get_firestore_client
import pandas as pd
from datetime import datetime
import uuid
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
# --- Helper functions ---
def get_dot(category):
    """Returns a colored emoji dot based on the category string."""
    if category == 'Red': return "🔴"
    elif category == 'Yellow': return "🟡"
    else: return "🟢"

def update_category(collection, doc_id, key):
    """Callback function to update a document's category in Firestore."""
    new_category = st.session_state[key]
    db.collection(collection).document(doc_id).update({"category": new_category})
    st.toast("Category updated!", icon="✅")

# --- Page Configuration and Authentication ---
st.set_page_config(
    page_title="Patient Dashboard",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

# --- Initialize Session State for Family Tree ---
if 'viewing_group_id' not in st.session_state:
    st.session_state.viewing_group_id = None

# --- Main Page Layout ---
tab1, tab2, tab3 = st.tabs(["Medical Records 🩺", "Private Notes 🧠", "Family Tree Group 🌳"])


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

    # --- Records Display ---
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
    st.subheader("🤧 Allergies & Conditions")
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
# --- TAB 2: Private Notes ---
# =================================================================================================
with tab2:
    st.header("My Private Mental Health Notes")
    st.caption("This is a safe and private space for your thoughts. These notes are not shared with your doctor.")
    st.markdown("---")

    with st.form("mental_health_note_form", clear_on_submit=True):
        note_content = st.text_area("Write down your thoughts and feelings...", height=200)
        if st.form_submit_button("Save Note") and note_content:
            db.collection("mental_health_notes").add({"patient_id": patient_id, "note": note_content, "timestamp": datetime.now()})
            st.success("Your note has been saved successfully!")
    st.markdown("---")

    st.subheader("Your Past Entries")
    notes_ref = db.collection("mental_health_notes").where(filter=FieldFilter("patient_id", "==", patient_id)).order_by("timestamp", direction="DESCENDING").stream()
    for note_doc in notes_ref:
        note = note_doc.to_dict()
        entry_date = note['timestamp'].strftime("%B %d, %Y at %I:%M %p")
        with st.expander(f"**Note from: {entry_date}**"):
            st.write(note['note'])


# =================================================================================================
# --- TAB 3: Family Tree Group ---
# =================================================================================================
with tab3:
    st.header("Family Tree Groups")
    st.caption("Create or join groups to share health information with family members.")

    # --- View a specific group ---
    if st.session_state.viewing_group_id:
        group_id = st.session_state.viewing_group_id
        group_doc = db.collection("family_groups").document(group_id).get()
        st.subheader(f"Managing Group: *{group_doc.to_dict().get('group_name')}*")

        if st.button("⬅️ Back to All Groups"):
            st.session_state.viewing_group_id = None
            st.rerun()

        # --- Add new member form ---
        with st.expander("Add a new family member to this group"):
            with st.form("add_member_form", clear_on_submit=True):
                new_member_id = st.text_input("New Member's Patient ID")
                relationship = st.text_input("Their relationship to you (e.g., Father, Sister, Son)")
                if st.form_submit_button("Add Member"):
                    if new_member_id and relationship:
                        new_member_ref = db.collection("patients").document(new_member_id)
                        new_member_doc = new_member_ref.get()
                        if not new_member_doc.exists:
                            st.error("Patient ID not found. Please check and try again.")
                        else:
                            # Add member to group's subcollection
                            new_member_name = new_member_doc.to_dict().get('Name', 'N/A')
                            db.collection("family_groups").document(group_id).collection("members").document(new_member_id).set({
                                "name": new_member_name,
                                "relationship": relationship,
                                "relative_to_id": patient_id, # The person adding them
                                "added_at": datetime.now()
                            })
                            # Update the new member's own profile with the group ID
                            new_member_ref.update({"family_groups": firestore.ArrayUnion([group_id])})
                            st.success(f"Added {new_member_name} to the group!")
                            st.rerun()

        # --- List current members ---
        st.markdown("---")
        st.subheader("Group Members")
        members_ref = db.collection("family_groups").document(group_id).collection("members").stream()
        members_list = [m.to_dict() for m in members_ref]
        # Fetch names for the 'relative_to_id' for better display
        relative_ids = {m['relative_to_id'] for m in members_list if 'relative_to_id' in m}
        relatives_map = {}
        for rid in relative_ids:
            rel_doc = db.collection('patients').document(rid).get()
            if rel_doc.exists:
                relatives_map[rid] = rel_doc.to_dict().get('Name', 'Unknown')

        h_cols = st.columns([2,2,2]); h_cols[0].markdown("**Name**"); h_cols[1].markdown("**Relationship**"); h_cols[2].markdown("**Relative To**")
        for member in members_list:
            r_cols = st.columns([2,2,2])
            r_cols[0].write(member.get('name'))
            r_cols[1].write(member.get('relationship'))
            relative_name = relatives_map.get(member.get('relative_to_id'), "N/A")
            r_cols[2].write(relative_name)

    # --- View all groups and create new ones ---
    else:
        with st.expander("Create a New Family Group", expanded=False):
            with st.form("new_group_form", clear_on_submit=True):
                group_name = st.text_input("New Group Name (e.g., Paternal Side, Immediate Family)")
                if st.form_submit_button("Create Group"):
                    if group_name:
                        # Create the group document
                        new_group_ref = db.collection("family_groups").document()
                        new_group_ref.set({
                            "group_name": group_name,
                            "creator_id": patient_id,
                            "created_at": datetime.now()
                        })
                        # Add the creator as the first member
                        new_group_ref.collection("members").document(patient_id).set({
                            "name": patient_name,
                            "relationship": "Self",
                            "relative_to_id": patient_id,
                            "added_at": datetime.now()
                        })
                        # Update the patient's own profile with the new group ID
                        patient_ref.update({"family_groups": firestore.ArrayUnion([new_group_ref.id])})
                        st.success(f"Group '{group_name}' created successfully!")
                        st.rerun()

        st.markdown("---")
        st.subheader("Your Existing Groups")
        try:
            patient_doc_data = patient_ref.get().to_dict()
            my_group_ids = patient_doc_data.get('family_groups', [])
            if not my_group_ids:
                st.info("You are not part of any family groups yet. Create one above to get started.")
            else:
                for group_id in my_group_ids:
                    group_doc = db.collection("family_groups").document(group_id).get()
                    if group_doc.exists:
                        g_cols = st.columns([3,1])
                        g_cols[0].write(f"**{group_doc.to_dict().get('group_name')}**")
                        if g_cols[1].button("View/Manage", key=f"view_{group_id}"):
                            st.session_state.viewing_group_id = group_id
                            st.rerun()
        except Exception as e:
            st.error("Could not load your family groups. Ensure your patient profile is set up correctly.")
            st.write(e)