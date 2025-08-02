import streamlit as st
from streamlit_extras.switch_page_button import switch_page

# Set page config
st.set_page_config(page_title="Login - Mangools Style", page_icon="🔐", layout="centered")

# CSS Styling
st.markdown("""
    <style>
        .main {
            background-color: #fff5eb;
            font-family: 'Segoe UI', sans-serif;
        }
        
        .login-title {
            font-size: 2em;
            font-weight: 600;
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .logo-bar {
            height: 10px;
            background: linear-gradient(to right, #ff6f61, #ffcc33);
            border-radius: 0 0 10px 10px;
            margin-bottom: 30px;
        }
        .btn-green {
            background: linear-gradient(to right, #00c853, #64dd17);
            color: white;
            border: none;
            width: 100%;
            padding: 0.75rem;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
        }
        .footer-links {
            text-align: center;
            margin-top: 1rem;
            font-size: 0.9rem;
        }
        .footer-links a {
            color: #4A90E2;
            margin: 0 10px;
            text-decoration: none;
        }
        .tools-bar {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 2rem;
        }
        .tool-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            font-size: 0.9rem;
        }
    </style>
""", unsafe_allow_html=True)

# Logo bar
#st.markdown('<div class="logo-bar"></div>', unsafe_allow_html=True)

# Login box
with st.container():
    #st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Good to see you again</div>', unsafe_allow_html=True)

    email = st.text_input("Your email", placeholder="e.g. elon@tesla.com")
    password = st.text_input("Your password", type="password", placeholder="e.g. ilovemangools123")

    if st.button("Sign in", key="signin", use_container_width=True):
        st.success("Signed in!")

    st.markdown('<div class="footer-links">'
                '<a href="#">Don\'t have an account?</a>'
                '<a href="#">Forgot password?</a>'
                '</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close login box

