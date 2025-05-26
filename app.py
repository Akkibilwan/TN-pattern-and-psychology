import streamlit as st
import os
import io
import json
import base64
import requests
from PIL import Image
import openai
import google.generativeai as genai

# --- Configuration & Credentials ---
st.set_page_config(
    page_title="Multi-Thumbnail Analyzer & Prompt Generator",
    page_icon="🖼️",
    layout="wide"
)

# Custom CSS (Dark Mode)
st.markdown("""
<style>
    .main { background-color: #0f0f0f; color: #f1f1f1; }
    .stApp { background-color: #0f0f0f; }
    h1, h2, h3, h4, h5, h6 { color: #f1f1f1; font-family: 'Roboto', sans-serif; }
    p, li, div, label { color: #aaaaaa; }
    .stButton>button {
        background-color: #303030;
        color: #f1f1f1;
        border: 1px solid #505050;
    }
    .stButton>button:hover {
        background-color: #505050;
        border: 1px solid #707070;
    }
    .uploaded-image-container {
        border: 1px solid #303030;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #181818;
    }
    .prompt-section {
        background-color: #202020;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .prompt-section h4 {
        margin-top: 0;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# --- Client Setup ---
def setup_openai():
    key = st.sidebar.text_input("OpenAI API Key", type="password")
    if key:
        openai.api_key = key
    else:
        st.sidebar.error("Provide OpenAI API key for analysis & generation.")

# --- Utilities ---
def encode_image_to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

# --- Analysis & Generation ---
def analyze_psychology(image_b64, filename):
    prompt = f"You are an expert in visual communication, marketing psychology, and digital design. " \
             f"Analyze this thumbnail image (base64) and identify its psychology and pattern. Provide JSON with keys: 'dominant_colors', 'composition', 'text_style', 'background_effects', 'branding', 'emotional_impact', 'contrast_usage', 'intrigue_narrative'."  
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role":"user", "content": prompt}
        ],
        max_tokens=500
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except:
        return {'error': resp.choices[0].message.content}


def synthesize_pattern(analyses):
    prompt = "You are an expert in visual design psychology. Given these analyses JSON list, identify common patterns and psychological strategies. Output a concise cue for thumbnail generation.\n" + json.dumps(analyses)
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role":"user","content":prompt}],
        max_tokens=300
    )
    return resp.choices[0].message.content


def generate_thumbnail(prompt_text):
    img_resp = openai.Image.create(
        model="gpt_image_1",
        prompt=prompt_text,
        n=1,
        size="1024x576"
    )
    return img_resp['data'][0]['url']

# --- Main App ---
def main():
    st.title("🖼️ Psychology-Driven Thumbnail Analyzer & Generator")
    setup_openai()

    uploaded = st.file_uploader("Upload thumbnails (JPG/PNG)", type=["jpg","png","jpeg"], accept_multiple_files=True)
    if uploaded:
        if st.button("Analyze & Generate"):
            analyses = []
            for file in uploaded:
                img_bytes = file.read()
                img_b64 = encode_image_to_base64(img_bytes)
                analysis = analyze_psychology(img_b64, file.name)
                analyses.append(analysis)
                st.write(f"**Analysis for {file.name}:**")
                st.json(analysis)

            pattern_prompt = synthesize_pattern(analyses)
            st.write("**Synthesized Pattern & Psychology Prompt:**")
            st.markdown(pattern_prompt)

            st.write("**Generating New Thumbnail...**")
            thumb_url = generate_thumbnail(pattern_prompt)
            st.image(thumb_url, caption="Generated Thumbnail", use_column_width=True)

    else:
        st.info("Upload one or more thumbnail images to begin.")

if __name__ == "__main__":
    main()
