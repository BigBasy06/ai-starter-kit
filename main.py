import base64
import io
import os

import streamlit as st

# --- EXTERNAL LIBS ---
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

# --- LOCAL MODULES ---
try:
    from utils import convert_pdf_to_image, process_image, sanitize_latex
except ImportError:
    st.error(
        "⚠️ SYSTEM ERROR: 'utils.py' not found. Ensure all files are in the directory."
    )
    st.stop()

# --- 1. CONFIGURATION ---
load_dotenv()

st.set_page_config(
    page_title="Nexus AI // Architect Edition",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_system_prompt():
    try:
        with open("system_instruction.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "You are an expert AI assistant. Solve the problem step-by-step using LaTeX."


try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 2. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ NEXUS CONTROL")

    # OpenAI Key Logic
    api_key = st.text_input("OpenAI API Key", type="password", help="sk-...")
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    st.markdown("---")
    model = st.selectbox("Neural Model", ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])
    system_instruction = st.text_area(
        "System Protocol", value=load_system_prompt(), height=150
    )
    st.caption("v1.0.0 | OpenAI Engine")


# --- 3. HELPER: IMAGE ENCODER ---
def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


# --- 4. MAIN INTERFACE ---
st.markdown("# ⚡ NEXUS AI // ARCHITECT")
st.markdown("### `SYSTEM STATUS: ONLINE`")

col1, col2 = st.columns([1, 1])

# --- LEFT COLUMN: INPUT ---
with col1:
    st.subheader("Input Stream")
    uploaded_file = st.file_uploader(
        "Upload Data (Image/PDF)", type=["png", "jpg", "jpeg", "pdf"]
    )
    user_context = st.text_area(
        "Additional Context", value="Analyze this. Solve step-by-step.", height=100
    )
    execute_btn = st.button("EXECUTE AGENT", type="primary", use_container_width=True)

    vision_input = None
    display_image = None

    if uploaded_file:
        file_bytes = uploaded_file.read()
        if uploaded_file.type == "application/pdf":
            with st.spinner("Rasterizing PDF..."):
                display_image, status = convert_pdf_to_image(file_bytes)
        else:
            display_image = Image.open(io.BytesIO(file_bytes))
            status = "SUCCESS"

        # Safe Processing Block
        if status == "SUCCESS" and display_image:
            optimized_img, opt_status = process_image(display_image)

            if optimized_img is not None:
                st.image(
                    optimized_img, caption="Ingested Data", use_container_width=True
                )
                vision_input = encode_image(optimized_img)
            else:
                st.error(f"Image Optimization Failed: {opt_status}")
        else:
            st.error(f"Input Error: {status}")

# --- RIGHT COLUMN: OUTPUT ---
with col2:
    st.subheader("Reasoning Trace")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if execute_btn:
        if not api_key:
            st.warning("⚠️ ACCESS DENIED: Missing OpenAI API Key.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": user_context})
        with st.chat_message("user"):
            st.write(user_context)

        client = OpenAI(api_key=api_key)

        # Construct Payload
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": [{"type": "text", "text": user_context}]},
        ]

        if vision_input:
            messages[0]["content"] += "\n[IMAGE CONTEXT PROVIDED]"
            messages[1]["content"].append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{vision_input}"},
                }
            )

        with st.chat_message("assistant"):
            response_box = st.empty()
            full_response = ""

            try:
                stream = client.chat.completions.create(
                    model=model, messages=messages, stream=True
                )

                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        response_box.markdown(full_response + "▌")

                clean_response = sanitize_latex(full_response)
                response_box.markdown(clean_response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": clean_response}
                )

            except Exception as e:
                st.error(f"API HANDSHAKE FAILED: {e}")
