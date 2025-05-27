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
    api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = st.sidebar.text_input(
            "OpenAI API key:", type="password", key="openai_key_input"
        )
    if not api_key:
        st.sidebar.error("API key is required.")
        return None
    return openai.OpenAI(api_key=api_key)

def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")

def analyze_image(client, image_b64: str, filename: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert in visual communication and marketing psychology."},
            {"role": "user", "content": f"Analyze '{filename}' for subject, colors, composition, text, mood, and psychological hooks."},
            {"role": "user", "content": f"<IMAGE_DATA>data:image/jpeg;base64,{image_b64}</IMAGE_DATA>"},
        ],
        max_tokens=600
    )
    return resp.choices[0].message.content.strip()

def synthesize_patterns(client, analyses: list[str]) -> dict:
    # Truncate each analysis to ~1500 chars to keep context small
    truncated = [(d[:1500] + "…") if len(d)>1500 else d for d in analyses]
    joined = "\n---\n".join(f"Analysis #{i+1}:\n{d}" for i, d in enumerate(truncated))
    prompt = (
        "You are an expert in marketing psychology and design. "
        "From the provided analyses, (1) summarize common visual patterns and psychological hooks, "
        "(2) produce one concise image-generation prompt to recreate that style. "
        "Return JSON with keys \"analysis_summary\" and \"generation_prompt\"."
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": joined},
        ],
        max_tokens=800
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        # Fallback: wrap entire text into summary
        text = resp.choices[0].message.content
        return {"analysis_summary": text, "generation_prompt": text}

def generate_thumbnail(client, prompt: str) -> Image.Image:
    resp = client.images.generate(
        model="gpt_image_1",
        prompt=prompt,
        size="1024x576",
        n=1
    )
    img_bytes = base64.b64decode(resp.data[0].b64_json)
    return Image.open(io.BytesIO(img_bytes))

def main():
    st.title("🖼️ Thumbnail Analyzer & Generator")
    st.markdown(
        "1. Upload thumbnails → 2. Get GPT-4 Vision analyses → "
        "3. Synthesize common patterns → 4. Generate new thumbnail with gpt_image_1."
    )

    client = setup_openai_client()
    if not client:
        return

    if 'analyses' not in st.session_state:
        st.session_state.analyses = []

    uploads = st.file_uploader(
        "Upload JPG/PNG thumbnails", type=["jpg","png","jpeg"], accept_multiple_files=True
    )

    if uploads:
        new_files = [
            (f.name, f.read()) for f in uploads
            if not any(a['name']==f.name and a['size']==f.size for a in st.session_state.analyses)
        ]
        if new_files and st.button(f"Analyze {len(new_files)} New"):
            with st.spinner("Analyzing…"):
                for name, data in new_files:
                    b64 = encode_image_to_base64(data)
                    desc = analyze_image(client, b64, name)
                    st.session_state.analyses.append({"name": name, "size": len(data), "desc": desc})
            st.success("Done!")

    if st.session_state.analyses:
        st.markdown("### Individual Analyses")
        for a in st.session_state.analyses:
            st.markdown(f"**{a['name']}**")
            with st.expander("View analysis"):
                st.write(a['desc'])

        if st.button("Synthesize & Generate"):
            with st.spinner("Synthesizing…"):
                synthesis = synthesize_patterns(client, [a['desc'] for a in st.session_state.analyses])
            st.subheader("Common Patterns & Psychology")
            st.write(synthesis["analysis_summary"])
            st.subheader("Generated Thumbnail")
            thumb = generate_thumbnail(client, synthesis["generation_prompt"])
            st.image(thumb, use_column_width=True)
            st.markdown(f"**Prompt:** `{synthesis['generation_prompt']}`")

    st.sidebar.info("Uses only OpenAI: GPT-4 Vision for analysis and gpt_image_1 for generation.")

if __name__ == "__main__":
    main()
