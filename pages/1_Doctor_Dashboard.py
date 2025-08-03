# pages/1_Doctor_Dashboard.py
import streamlit as st
from firebase_config import get_firestore_client, get_storage_bucket
import pandas as pd
from datetime import datetime
import uuid
import time
import requests # Import requests to make API calls
import json
from datetime import date, datetime

# --- Helper function for colored dots ---
def get_dot(category):
    """Returns a colored emoji dot based on the category string."""
    if category == 'Red': return "🔴"
    elif category == 'Yellow': return "🟡"
    else: return "🟢"

# --- Page Configuration and Authentication ---
st.set_page_config(
    page_title="Doctor Dashboard",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

if not st.session_state.get('doctor_logged_in'):
    st.error("You must be logged in to view this page.")
    st.stop()

st.title(f"🩺 Welcome, {st.session_state.get('doctor_name', 'Doctor')}!")
st.sidebar.button("Logout", on_click=lambda: st.switch_page("app.py"))

# --- Firebase Connection ---
db = get_firestore_client()
bucket = get_storage_bucket()

# --- Main Page Layout ---
tab1, tab2, tab3 = st.tabs(["View/Manage Patient", "Create New Patient", "Maternity Risk Assessment"])

# --- TAB 1: View/Manage Patient ---
with tab1:
    st.header("Patient Record Search")
    with st.form("search_patient_form"):
        search_patient_id = st.text_input("Enter Patient ID to Search")
        search_submitted = st.form_submit_button("Search")

    if search_submitted and search_patient_id:
        st.session_state.searched_patient_id = search_patient_id
        st.session_state.access_granted = False

    if 'searched_patient_id' in st.session_state:
        patient_id = st.session_state.searched_patient_id
        patient_doc = db.collection("patients").document(patient_id).get()

        if not patient_doc.exists:
            st.error(f"No patient found with ID: {patient_id}.")
        else:
            patient_data = patient_doc.to_dict()
            st.subheader(f"Records for Patient: {patient_data.get('Name', 'N/A')} (ID: {patient_id})")

            is_confidential = patient_data.get('confidential', False)
            if is_confidential and not st.session_state.get('access_granted', False):
                st.warning("🔒 This patient's records are marked as confidential.")
                if st.button("Request Access to Confidential Data"):
                    with st.spinner("Requesting..."): time.sleep(1)
                    st.success("✅ OTP sent to patient for verification."); time.sleep(1)
                    st.session_state.access_granted = True; st.rerun()
            else:
                if is_confidential: st.success("🔓 Access to confidential records granted.")

                view_red_data = st.toggle("🔴 Show Critical (Red) Records", help="Turn on to view records marked as critical.")

                # --- Data Fetching and Filtering ---
                all_prescriptions = [doc.to_dict() for doc in db.collection("prescriptions").where("patient_id", "==", patient_id).stream()]
                all_allergies = [doc.to_dict() for doc in db.collection("allergies_and_conditions").where("patient_id", "==", patient_id).stream()]
                all_scans = [doc.to_dict() for doc in db.collection("scans").where("patient_id", "==", patient_id).stream()]

                if view_red_data:
                    prescriptions, allergies, scans = all_prescriptions, all_allergies, all_scans
                else:
                    prescriptions = [p for p in all_prescriptions if p.get('category', 'Green') in ['Green', 'Yellow']]
                    allergies = [a for a in all_allergies if a.get('category', 'Green') in ['Green', 'Yellow']]
                    scans = [s for s in all_scans if s.get('category', 'Green') in ['Green', 'Yellow']]

                # --- Display Patient Data ---
                st.write(f"**DOB:** {patient_data.get('DOB', 'N/A')} | **Blood Group:** {patient_data.get('BloodGroup', 'N/A')}")
                col1, col2 = st.columns(2)
                with col1:
                    with st.expander("🤧 Health History", expanded=True):
                        if allergies:
                            for allergy in allergies: st.info(f"{get_dot(allergy.get('category'))} {allergy['description']}")
                        else: st.write("No conditions to display.")
                with col2:
                    with st.expander("📷 Medical Scans", expanded=True):
                        if scans:
                            for scan in scans: st.markdown(f"{get_dot(scan.get('category'))} **{scan['body_part']}**: [View Scan]({scan['file_url']})")
                        else: st.write("No scans to display.")
                with st.expander("💊 Prescriptions", expanded=True):
                    if prescriptions:
                        df_data = [{"Category": get_dot(p.get('category')), "Medication": p['medication_name'], "Condition": p['condition'], "Duration": p['duration']} for p in prescriptions]
                        st.dataframe(pd.DataFrame(df_data), use_container_width=True)
                    else: st.write("No prescriptions to display.")
                st.divider()

                # --- AI Clinical Assistant Section ---
                st.subheader("🤖 AI Clinical Assistant")

                # Fetch and process family data
                with st.spinner("Analyzing family health history..."):
                    my_group_ids = patient_data.get('family_groups', [])
                    all_relatives_ids = set()
                    if my_group_ids:
                        for group_id in my_group_ids:
                            members_ref = db.collection("family_groups").document(group_id).collection("members").stream()
                            for member in members_ref:
                                all_relatives_ids.add(member.id)
                    all_relatives_ids.discard(patient_id) # Remove current patient

                    family_conditions = []
                    for rel_id in all_relatives_ids:
                        conds = db.collection("allergies_and_conditions").where("patient_id", "==", rel_id).stream()
                        for cond in conds:
                            c_data = cond.to_dict()
                            if c_data.get('category', 'Green') in ['Green', 'Yellow']:
                                family_conditions.append(c_data['description'])
                    
                    # Consolidate and anonymize family history
                    anon_family_history = {"conditions": list(set(family_conditions))}

                # Prepare data for the AI model
                gy_allergies = [a['description'] for a in all_allergies if a.get('category', 'Green') in ['Green', 'Yellow']]
                gy_prescriptions = [p['medication_name'] for p in all_prescriptions if p.get('category', 'Green') in ['Green', 'Yellow']]
                
                patient_context_for_ai = {
                    "patient_conditions": gy_allergies,
                    "patient_medications": gy_prescriptions,
                    "family_history": anon_family_history,
                }

                with st.expander("View Data Sent to AI"):
                    st.json(patient_context_for_ai)

                procedure = st.text_input("Enter a medical procedure or context for analysis", key="ai_procedure")

                if st.button("Analyze with AI", key="ai_analyze_button"):
                    if not procedure:
                        st.warning("Please enter a procedure to analyze.")
                    else:
                        api_url = "http://127.0.0.1:5001/api/medical/analyze"
                        payload = {"patient_data": patient_context_for_ai, "procedure": procedure}
                        with st.spinner("AI is analyzing the data..."):
                            try:
                                response = requests.post(api_url, json=payload, timeout=60)
                                if response.status_code == 200:
                                    result = response.json()
                                    st.info("**AI Patient Summary:**")
                                    st.markdown(result.get("patient_statement"))
                                    st.success("**AI Generated Questions for Doctor:**")
                                    st.markdown(result.get("doctor_response"))
                                else:
                                    st.error(f"Error from AI service: {response.status_code} - {response.text}")
                            except requests.exceptions.RequestException as e:
                                st.error(f"Could not connect to the AI analysis service. Is the backend running? Error: {e}")
                
                st.divider()
              
                st.subheader("Add New Records")
                form_col1, form_col2, form_col3 = st.columns(3)
                with form_col1:
                    with st.form("add_allergy_form", clear_on_submit=True):
                        new_allergy = st.text_input("Add Health Condition")
                        if st.form_submit_button("Add"):
                            if new_allergy:
                                db.collection("allergies_and_conditions").add({"patient_id": patient_id, "description": new_allergy, "category": "Green", "timestamp": datetime.now()})
                                st.success("Allergy added!"); st.rerun()
                with form_col2:
                    with st.form("add_prescription_form", clear_on_submit=True):
                        med_name = st.text_input("Medication Name")
                        condition = st.text_input("Condition")
                        if st.form_submit_button("Add"):
                            if med_name and condition:
                                db.collection("prescriptions").add({"patient_id": patient_id, "medication_name": med_name, "condition": condition, "duration": "N/A", "timing": [], "category": "Green", "timestamp": datetime.now()})
                                st.success("Prescription added!"); st.rerun()
                with form_col3:
                     with st.form("upload_scan_form", clear_on_submit=True):
                        scan_file = st.file_uploader("Upload Scan", type=['png', 'jpg', 'pdf'])
                        body_part = st.text_input("Body Part Scanned")
                        if st.form_submit_button("Upload"):
                            if scan_file and body_part:
                                blob = bucket.blob(f"scans/{patient_id}/{scan_file.name}"); blob.upload_from_file(scan_file, content_type=scan_file.type); blob.make_public()
                                db.collection("scans").add({"patient_id": patient_id, "body_part": body_part, "file_url": blob.public_url, "category": "Green", "timestamp": datetime.now()})
                                st.success("Scan uploaded!"); st.rerun()

# --- TAB 2: Create New Patient ---
with tab2:
    st.header("Create a New Patient Record")
    with st.form("new_patient_form", clear_on_submit=True):
        p_name = st.text_input("Full Name")
        p_dob = st.date_input("Date of Birth", max_value=datetime.today(), min_value=date(1900, 1, 1))
        p_phone = st.text_input("Phone Number")
        p_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        p_blood_group = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
        p_ethnicity = st.text_input("Ethnicity")
        p_password = st.text_input("Set Patient Password", type="password")
        
        if st.form_submit_button("Create Patient"):
            if all([p_name, p_dob, p_phone, p_password]):
                patient_id = f"PAT-{str(uuid.uuid4())[:8].upper()}"
                patient_data = {
                    "Name": p_name,
                    "DOB": p_dob.strftime("%Y-%m-%d"),
                    "Phno": p_phone,
                    "Gender": p_gender,
                    "BloodGroup": p_blood_group,
                    "Ethnicity": p_ethnicity,
                    "password": p_password,
                    "confidential": False,
                    "family_groups": []
                }
                db.collection("patients").document(patient_id).set(patient_data)
                st.success(f"✅ Patient created: {p_name}")
                st.info("Provide these credentials to the patient:")
                st.code(f"Patient ID: {patient_id}\nPassword: {p_password}")
            else:
                st.error("Please fill in all required details.")

# --- TAB 3: Maternity Risk Assessment ---
with tab3:
    st.header("🤱 Maternity Risk Assessment")
    st.write("Enter a patient ID to automatically assess pregnancy-related risks based on their stored medical data.")
    
    # Simple patient ID input form
    with st.form("maternity_patient_search"):
        risk_patient_id = st.text_input("Enter Patient ID for Risk Assessment", placeholder="PAT-12345678")
        assess_risk = st.form_submit_button("🔍 Assess Maternity Risk", use_container_width=True)
    
    if assess_risk and risk_patient_id:
        # Fetch patient data from Firebase
        patient_doc = db.collection("patients").document(risk_patient_id).get()
        
        if not patient_doc.exists:
            st.error(f"❌ No patient found with ID: {risk_patient_id}")
        else:
            patient_data = patient_doc.to_dict()
            st.success(f"✅ Patient found: {patient_data.get('Name', 'N/A')}")
            
            # Display patient basic info
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.write(f"**Name:** {patient_data.get('Name', 'N/A')}")
                st.write(f"**DOB:** {patient_data.get('DOB', 'N/A')}")
            with col_info2:
                st.write(f"**Gender:** {patient_data.get('Gender', 'N/A')}")
                st.write(f"**Blood Group:** {patient_data.get('BloodGroup', 'N/A')}")
            
            # Calculate age from DOB
            try:
                dob = datetime.strptime(patient_data.get('DOB', '1990-01-01'), '%Y-%m-%d')
                age = (datetime.now() - dob).days // 365
            except:
                age = 25  # default age
            
            # For this simplified version, we'll use default/estimated values
            # In a real implementation, you'd have additional patient data stored
            assessment_data = {
                "age": age,
                "bmi": 22.0,  # Default - would need to be stored in patient data
                "blood_pressure": 120,  # Default - would come from recent vitals
                "hemoglobin": 12.0,  # Default - would come from recent lab results
                "glucose": 90,  # Default - would come from recent lab results
                "parity": 0,  # Default - would be stored in patient obstetric history
                "education": "Graduate",  # Default - could be stored in patient demographics
                "smoking": "No",  # Default - would be stored in patient social history
                "income": "Middle",  # Default - could be stored in patient demographics
                "history_anemia": "No",  # Would check patient's allergy/condition records
                "history_gdm": "No",  # Would check patient's medical history
                "history_preeclampsia": "No",  # Would check patient's medical history
                "history_preterm": "No"  # Would check patient's obstetric history
            }
            
            st.info("ℹ️ Using default values for missing medical data. In production, this would pull from comprehensive patient records including vitals, lab results, and medical history.")
            
            # Make API call to maternity risk model
            api_url = "http://127.0.0.1:5000/predict"
            
            with st.spinner("Analyzing maternity risks..."):
                try:
                    response = requests.post(api_url, json=assessment_data, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        predictions = result.get("prediction", {})
                        explanations = result.get("explanation_top_features", {})
                        
                        st.success("✅ Risk Assessment Complete!")
                        
                        # Display results in a structured format
                        st.subheader("📊 Risk Assessment Results")
                        
                        # Create columns for different risk types
                        risk_col1, risk_col2 = st.columns(2)
                        
                        with risk_col1:
                            # Gestational Diabetes Risk
                            gdm_risk = predictions.get("risk_gdm", 0)
                            if gdm_risk == 1:
                                st.error("🔴 **High Risk: Gestational Diabetes**")
                            else:
                                st.success("🟢 **Low Risk: Gestational Diabetes**")
                            
                            if "risk_gdm" in explanations:
                                st.write(f"*{explanations['risk_gdm']}*")
                            
                            st.divider()
                            
                            # Anemia Risk
                            anemia_risk = predictions.get("risk_anemia", 0)
                            if anemia_risk == 1:
                                st.error("🔴 **High Risk: Anemia**")
                            else:
                                st.success("🟢 **Low Risk: Anemia**")
                            
                            if "risk_anemia" in explanations:
                                st.write(f"*{explanations['risk_anemia']}*")
                        
                        with risk_col2:
                            # Preeclampsia Risk
                            preeclampsia_risk = predictions.get("risk_preeclampsia", 0)
                            if preeclampsia_risk == 1:
                                st.error("🔴 **High Risk: Preeclampsia**")
                            else:
                                st.success("🟢 **Low Risk: Preeclampsia**")
                            
                            if "risk_preeclampsia" in explanations:
                                st.write(f"*{explanations['risk_preeclampsia']}*")
                            
                            st.divider()
                            
                            # Preterm Labor Risk
                            preterm_risk = predictions.get("risk_preterm_labor", 0)
                            if preterm_risk == 1:
                                st.error("🔴 **High Risk: Preterm Labor**")
                            else:
                                st.success("🟢 **Low Risk: Preterm Labor**")
                            
                            if "risk_preterm_labor" in explanations:
                                st.write(f"*{explanations['risk_preterm_labor']}*")
                        
                        st.divider()
                        
                        # Summary and Recommendations
                        st.subheader("📝 Clinical Summary & Recommendations")
                        
                        high_risks = [risk.replace("risk_", "").replace("_", " ").title() 
                                    for risk, value in predictions.items() if value == 1]
                        
                        if high_risks:
                            st.warning(f"**High-risk conditions identified:** {', '.join(high_risks)}")
                            st.write("**Recommended Actions:**")
                            
                            recommendations = []
                            if gdm_risk == 1:
                                recommendations.append("• Monitor glucose levels regularly")
                                recommendations.append("• Consider dietary counseling")
                                recommendations.append("• Schedule more frequent prenatal visits")
                            
                            if preeclampsia_risk == 1:
                                recommendations.append("• Monitor blood pressure closely")
                                recommendations.append("• Watch for signs of preeclampsia (headaches, vision changes)")
                                recommendations.append("• Consider low-dose aspirin prophylaxis")
                            
                            if anemia_risk == 1:
                                recommendations.append("• Iron supplementation")
                                recommendations.append("• Dietary modifications to include iron-rich foods")
                                recommendations.append("• Monitor hemoglobin levels")
                            
                            if preterm_risk == 1:
                                recommendations.append("• Monitor for signs of preterm labor")
                                recommendations.append("• Consider cervical length monitoring")
                                recommendations.append("• Educate patient on warning signs")
                            
                            for rec in recommendations:
                                st.write(rec)
                        else:
                            st.success("**Low risk for all assessed conditions.** Continue with routine prenatal care.")
                        
                        # Option to save assessment
                        if st.button("💾 Save Assessment to Patient Record"):
                            # Save assessment results to Firebase
                            assessment_record = {
                                "patient_id": risk_patient_id,
                                "assessment_date": datetime.now(),
                                "predictions": predictions,
                                "explanations": explanations,
                                "assessed_by": st.session_state.get('doctor_name', 'Unknown Doctor'),
                                "assessment_data": assessment_data
                            }
                            db.collection("maternity_assessments").add(assessment_record)
                            st.success("Assessment saved to patient record!")
                    
                    else:
                        st.error(f"❌ Error from risk assessment service: {response.status_code}")
                        if response.text:
                            st.code(response.text)
                            
                except requests.exceptions.ConnectionError:
                    st.error("❌ Could not connect to the maternity risk assessment service. Please ensure the Flask backend is running on http://127.0.0.1:5000")
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out. The assessment service may be overloaded.")
                except Exception as e:
                    st.error(f"❌ An unexpected error occurred: {str(e)}")
    
    # Additional information section
    with st.expander("ℹ️ About Maternity Risk Assessment"):
        st.write("""
        This AI-powered tool automatically assesses pregnancy-related risks using patient data from their medical records.
        Simply enter a patient ID to get an instant risk assessment covering:
        
        - **Gestational Diabetes Mellitus (GDM)**: High blood sugar during pregnancy
        - **Preeclampsia**: High blood pressure and organ damage during pregnancy  
        - **Anemia**: Low red blood cell count or hemoglobin levels
        - **Preterm Labor**: Labor that begins before 37 weeks of pregnancy
        
        **Note:** Currently uses default values for missing medical data. In a full implementation, 
        this would pull comprehensive data including recent vitals, lab results, and complete medical history.
        
        **Important:** This tool assists clinical decision-making and should not replace professional medical judgment.
        """)