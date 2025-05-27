# app.py
import streamlit as st
import os
import io
import base64
import json
from PIL import Image
import openai

# --- Configuration & Credentials ---
st.set_page_config(
    page_title="Multi-Thumbnail Analyzer & Prompt Generator",
    page_icon="🖼️",
    layout="wide"
)

def setup_openai_client():
    """Initialize and return an OpenAI client."""
    api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = st.sidebar.text_input(
            "Enter your OpenAI API key:", type="password", key="openai_key_input"
        )
    if not api_key:
        st.sidebar.error("OpenAI API key is required for analysis and image generation.")
        return None
    return openai.OpenAI(api_key=api_key)

# --- Helpers ---
def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")

def analyze_image(client, image_b64: str, filename: str) -> str:
    """Use GPT-4 Vision to analyze a single thumbnail."""
    system = "You are an expert in visual communication, marketing psychology, and digital design."
    user = (
        f"Analyze this YouTube thumbnail image named '{filename}' in detail. "
        "Describe its main subject, background, style, colors, any text present, composition, mood, "
        "and any psychological hooks used to grab attention."
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "user", "content": f"<IMAGE_DATA>data:image/jpeg;base64,{image_b64}</IMAGE_DATA>"}
        ],
        max_tokens=800
    )
    return resp.choices[0].message.content.strip()

def synthesize_patterns(client, analyses: list[str]) -> str:
    """
    Identify common patterns & psychology across all analyzed thumbnails,
    with truncation to avoid context-length errors.
    """
    # truncate each individual analysis to max_chars
    max_chars = 2000
    truncated = []
    for desc in analyses:
        if len(desc) > max_chars:
            truncated.append(desc[:max_chars] + "\n…(truncated)")
        else:
            truncated.append(desc)
    # join and then truncate whole payload
    joined = "\n\n---\n\n".join(f"Analysis #{i+1}:\n{d}" for i, d in enumerate(truncated))
    max_total = 100000
    if len(joined) > max_total:
        joined = joined[:max_total] + "\n\n…(overall analyses truncated to fit context limits.)"

    prompt = """You are an expert in visual communication, marketing psychology, and digital design.
Your task is to analyze a given set of thumbnail analyses, identifying common patterns and the underlying psychological strategies employed to capture attention and convey a message.

For all provided analyses:
1. Summarize the dominant visual patterns across all thumbnails.
2. Describe the shared psychological hooks (e.g., urgency, curiosity, drama).
3. Infer the target audience and how these techniques appeal to them.
4. Finally, craft a single, concise prompt that could be fed to an image-generation model to recreate a thumbnail using those patterns and psychology.

Return your answer as JSON with keys:
- "analysis_summary": the text summary (use numbered points).
- "generation_prompt": the single prompt string for image generation.
"""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": joined}
        ],
        max_tokens=1000
    )
    return resp.choices[0].message.content.strip()

def generate_thumbnail(client, prompt: str) -> Image.Image:
    """Use gpt_image_1 to generate a new thumbnail based on the synthesized prompt."""
    resp = client.images.generate(
        model="gpt_image_1",
        prompt=prompt,
        size="1024x576",  # 16:9 aspect
        n=1
    )
    b64 = resp.data[0].b64_json
    img_bytes = base64.b64decode(b64)
    return Image.open(io.BytesIO(img_bytes))

# --- Main App ---
def main():
    st.title("🖼️ Multi-Thumbnail Analyzer & Prompt Generator")
    st.markdown(
        "Upload one or more thumbnail images. The app will:\n"
        "1. Analyze each with GPT-4 Vision for visual & psychological breakdown.\n"
        "2. Identify common patterns & hooks across all thumbnails (with safe truncation).\n"
        "3. Generate a brand-new thumbnail replicating that psychology using gpt_image_1."
    )

    client = setup_openai_client()
    if not client:
        return

    if 'analyses' not in st.session_state:
        st.session_state.analyses = []

    uploads = st.file_uploader(
        "Upload thumbnail images (JPG, PNG)", 
        type=["jpg", "png", "jpeg"],
        accept_multiple_files=True
    )

    if uploads:
        new = []
        for f in uploads:
            data = f.read()
            if not any(a['name']==f.name and a['size']==f.size for a in st.session_state.analyses):
                new.append((f.name, data))
        if new and st.button(f"Analyze {len(new)} New Image(s)"):
            with st.spinner("Analyzing..."):
                for name, img_bytes in new:
                    b64 = encode_image_to_base64(img_bytes)
                    desc = analyze_image(client, b64, name)
                    st.session_state.analyses.append({
                        "name": name,
                        "size": len(img_bytes),
                        "desc": desc
                    })
            st.success("Analysis complete!")

    if st.session_state.analyses:
        st.markdown("---")
        st.subheader("🔍 Individual Analyses")
        for a in st.session_state.analyses:
            st.markdown(f"**{a['name']}**")
            with st.expander("View analysis"):
                st.write(a['desc'])

        st.markdown("---")
        if st.button("Identify Patterns & Generate Thumbnail"):
            with st.spinner("Synthesizing patterns..."):
                all_descs = [a['desc'] for a in st.session_state.analyses]
                synthesis = synthesize_patterns(client, all_descs)
                try:
                    obj = json.loads(synthesis)
                    summary = obj.get("analysis_summary", "")
                    gen_prompt = obj.get("generation_prompt", "")
                except json.JSONDecodeError:
                    summary = synthesis
                    gen_prompt = synthesis

            st.subheader("📊 Common Patterns & Psychology")
            st.markdown(summary)

            st.subheader("🎨 Generated Thumbnail")
            with st.spinner("Generating image..."):
                thumb = generate_thumbnail(client, gen_prompt)
                st.image(thumb, use_column_width=True)
                st.markdown(f"**Prompt used:**\n```\n{gen_prompt}\n```")

    st.sidebar.markdown("---")
    st.sidebar.info(
        "This app uses only OpenAI APIs: GPT-4 Vision for analysis and gpt_image_1 for thumbnail generation."
    )

if __name__ == "__main__":
    main()
