import streamlit as st
import openai
import base64
import json

# Streamlit page configuration
st.set_page_config(
    page_title="Thumbnail Analyzer & Prompt Generator",
    layout="wide"
)

# Initialize OpenAI API key
openai.api_key = st.secrets.get("OPENAI_API_KEY")

# Function to analyze a single thumbnail image
def analyze_thumbnail(image_bytes):
    # Encode image to base64 for embedding in prompt
    img_base64 = base64.b64encode(image_bytes).decode("utf-8")
    
    system_prompt = (
        "You are an expert in visual communication, marketing psychology, and digital design. "
        "Analyze the provided thumbnail image. "
        "For the given image, provide structured JSON with these keys: "
        "visual_elements, psychological_impact, emotional_resonance, intrigue_narrative, pattern_strategy."
    )

    user_prompt = (
        f"Here is the thumbnail image in base64 format: data:image/png;base64,{img_base64}\n"
        "Perform your analysis as specified."
    )

    response = openai.ChatCompletion.create(
        model="gpt-4o",  # Vision-capable model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    # Return the raw JSON content
    return response.choices[0].message.content

# Main application
st.title("Thumbnail Analyzer & GPT Prompt Generator")

# Upload multiple thumbnails
uploaded_files = st.file_uploader(
    "Upload thumbnail images (PNG, JPG, JPEG)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded_files:
    analyses = {}
    # Analyze each uploaded thumbnail
    for uploaded_file in uploaded_files:
        img_bytes = uploaded_file.read()
        with st.spinner(f"Analyzing {uploaded_file.name}..."):
            analysis_json = analyze_thumbnail(img_bytes)
        st.subheader(f"Analysis for {uploaded_file.name}")
        st.json(json.loads(analysis_json))
        analyses[uploaded_file.name] = json.loads(analysis_json)

    # Synthesize common patterns across all thumbnails
    synth_system = (
        "You are an expert in visual psychology and design strategy. "
        "Given multiple analyses of thumbnail images (in JSON), identify the most common visual patterns and psychological strategies. "
        "Provide a list of prompt templates that can recreate each identified pattern/psychology."
    )
    synth_user = (
        "Here are the analyses for each thumbnail (JSON mapping filename to analysis):\n" +
        json.dumps(analyses)
    )

    synth_resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": synth_system},
            {"role": "user", "content": synth_user}
        ]
    )

    common_prompts = synth_resp.choices[0].message.content
    st.subheader("Common Patterns & Generated Prompt Templates")
    st.write(common_prompts)

    # Allow the user to edit the combined prompt
    st.subheader("Customize & Generate Thumbnail")
    prompt_input = st.text_area(
        "Edit the prompt to replicate desired psychology and pattern:",
        value=common_prompts,
        height=200
    )

    if st.button("Generate Sample Thumbnail with GPT-Image-1"):  # Use gpt_image_1 model
        with st.spinner("Generating image..."):
            img_gen = openai.Image.create(
                model="gpt_image_1",
                prompt=prompt_input,
                n=1,
                size="512x512"
            )
        st.subheader("Generated Thumbnail Preview")
        st.image(img_gen.data[0].url, use_column_width=True)

    # Provide a reusable visual breakdown prompt
    breakdown_prompt = (
        "You are an expert in visual communication, marketing psychology, and digital design. "
        "Provide a detailed template for visual elements breakdown that can be used to analyze any thumbnail image. "
        "Include sections for color theory, composition, typography, iconography, and focal hierarchy."
    )
    st.subheader("Visual Breakdown Prompt Template")
    st.code(breakdown_prompt)
