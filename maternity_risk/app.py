from flask import Flask, request, jsonify
import joblib
import pandas as pd
import shap
import numpy as np
import traceback

# Load model and preprocessing tools
model = joblib.load("maternity_risk_model.pkl")
scaler = joblib.load("scaler.pkl")
label_encoders = joblib.load("label_encoders.pkl")

risk_cols = ['risk_gdm', 'risk_preeclampsia', 'risk_anemia', 'risk_preterm_labor']
explainers = [shap.Explainer(est) for est in model.estimators_]

# Natural language template for feature interpretations
feature_descriptions = {
    'age': 'older age',
    'bmi': 'higher BMI',
    'blood_pressure': 'elevated blood pressure',
    'hemoglobin': 'low hemoglobin levels',
    'glucose': 'higher glucose levels',
    'parity': 'number of previous births',
    'education': 'lower education level',
    'smoking': 'smoking history',
    'income': 'lower income',
    'history_anemia': 'past anemia history',
    'history_gdm': 'previous gestational diabetes',
    'history_preeclampsia': 'previous preeclampsia',
    'history_preterm': 'history of preterm delivery',
    # Add others based on your feature set
}

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        input_df = pd.DataFrame([data])

        # Apply encoders
        for col, le in label_encoders.items():
            if col in input_df.columns:
                input_df[col] = le.transform(input_df[col].astype(str))

        input_df.fillna(input_df.median(numeric_only=True), inplace=True)
        X_scaled = pd.DataFrame(scaler.transform(input_df), columns=input_df.columns)

        predictions = model.predict(X_scaled)[0]
        risk_output = {col: int(pred) for col, pred in zip(risk_cols, predictions)}

        summary_sentences = {}
        for i, risk in enumerate(risk_cols):
            risk_label = risk.replace("risk_", "")
            shap_vals = explainers[i](X_scaled)
            shap_values = shap_vals.values[0]
            top_indices = np.argsort(np.abs(shap_values))[::-1][:3]  # top 3 features

            phrases = []
            for idx in top_indices:
                feature = input_df.columns[idx]
                shap_val = shap_values[idx]
                desc = feature_descriptions.get(feature, feature.replace("_", " "))

                phrases.append(desc)

            explanation = " and ".join(phrases) if phrases else "No significant contributors identified"
            
            if int(risk_output[risk]) == 1:
                sentence = f"Increased risk of {risk_label} due to {explanation}."
            else:
                sentence = f"Reduced risk of {risk_label} due to {explanation}."
            
            summary_sentences[risk] = sentence



        return jsonify({
            'prediction': risk_output,
            'explanation_top_features': summary_sentences
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc()
        })

if __name__ == '__main__':
    app.run(debug=True)
