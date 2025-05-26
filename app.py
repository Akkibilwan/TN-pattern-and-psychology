import streamlit as st
import json
import base64
import openai

# --- Configuration & Credentials ---
st.set_page_config(
    page_title="Psychology-Driven Thumbnail Analyzer & Generator",
    page_icon="🖼️",
    layout="wide"
)

# Custom Dark Mode CSS
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
</style>
""", unsafe_allow_html=True)

# --- OpenAI Setup ---
def setup_openai():
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    if api_key:
        openai.api_key = api_key
    else:
        st.sidebar.error("Please enter your OpenAI API key.")

# --- Utility Functions ---
def encode_image_to_base64(bytes_data):
    return base64.b64encode(bytes_data).decode('utf-8')

# --- Analysis and Generation ---
def analyze_psychology(image_b64):
    prompt = (
        "You are an expert in visual communication, marketing psychology, and digital design. "
        "Analyze the given thumbnail (provided as base64). "
        "Identify its psychological strategies and return a JSON with keys: "
        "'dominant_colors', 'composition', 'text_style', 'background_effects', 'branding', "
        "'emotional_impact', 'contrast_usage', 'intrigue_narrative'."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt + "\n\n" + image_b64}],
        max_tokens=500
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return {"error": resp.choices[0].message.content}


def synthesize_pattern(analyses):
    prompt = (
        "You are an expert in marketing psychology. Given these analyses JSON list, "
        "identify common visual patterns and psychological strategies, and output a concise prompt "
        "to generate a new thumbnail replicating the same psychology:\n"
        + json.dumps(analyses)
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
    )
    return resp.choices[0].message.content


def generate_thumbnail(cue):
    resp = openai.Image.create(
        model="gpt_image_1",
        prompt=cue,
        n=1,
        size="1024x576"
    )
    return resp['data'][0]['url']

# --- Main Application ---
def main():
    st.title("🖼️ Psychology-Driven Thumbnail Analyzer & Generator")
    setup_openai()

    uploaded = st.file_uploader(
        "Upload thumbnail images (JPG/PNG)",
        type=["jpg","png","jpeg"],
        accept_multiple_files=True
    )

    if uploaded:
        if st.button("Analyze & Generate"):
            analyses = []
            for file in uploaded:
                bytes_data = file.read()
                b64 = encode_image_to_base64(bytes_data)
                analysis = analyze_psychology(b64)
                analyses.append(analysis)
                st.subheader(f"Analysis for {file.name}")
                st.json(analysis)

            cue = synthesize_pattern(analyses)
            st.subheader("Synthesized Generation Prompt")
            st.text(cue)

            st.subheader("Generated Thumbnail")
            url = generate_thumbnail(cue)
            st.image(url, use_column_width=True, caption="New Thumbnail")
    else:
        st.info("Please upload one or more thumbnail images.")

if __name__ == "__main__":
    main()
