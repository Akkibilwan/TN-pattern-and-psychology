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
    page_title="Thumbnail Analyzer & Generator",
    page_icon="🖼️",
    layout="wide"
)

def setup_openai_client():
    key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        key = st.sidebar.text_input("OpenAI API key:", type="password", key="key_input")
    if not key:
        st.sidebar.error("API key required.")
        return None
    return openai.OpenAI(api_key=key)

def encode_b64(data: bytes) -> str:
    return base64.b64encode(data).decode()

def analyze_image(client, b64: str, name: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system", "content":"You are an expert in visual communication and marketing psychology."},
            {"role":"user", "content":f"Analyze '{name}' for subject, colors, composition, text, mood, and psychological hooks."},
            {"role":"user", "content":f"<IMAGE_DATA>data:image/jpeg;base64,{b64}</IMAGE_DATA>"},
        ],
        max_tokens=600
    )
    return resp.choices[0].message.content.strip()

def synthesize_patterns(client, analyses: list[str]) -> dict:
    # only use up to the last 10 analyses
    subset = analyses[-10:]
    # truncate each to ~700 chars
    truncated = [(d[:700] + "…") if len(d)>700 else d for d in subset]
    joined = "\n---\n".join(f"Analysis #{i+1}:\n{d}" for i,d in enumerate(truncated))
    # ensure joined is under ~40000 chars
    if len(joined) > 40000:
        joined = joined[:40000] + "\n…(truncated)·"
    prompt = (
        "You are an expert in marketing psychology and design.\n"
        "From these analyses:\n"
        "1) Summarize common visual patterns & psychological hooks.\n"
        "2) Provide one concise image-generation prompt to recreate that style.\n"
        "Return JSON with keys \"analysis_summary\" and \"generation_prompt\"."
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system", "content":prompt},
            {"role":"user", "content":joined},
        ],
        max_tokens=800
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"analysis_summary": text, "generation_prompt": text}

def generate_thumbnail(client, prompt: str) -> Image.Image:
    resp = client.images.generate(
        model="gpt_image_1",
        prompt=prompt,
        size="1024x576",
        n=1
    )
    img = base64.b64decode(resp.data[0].b64_json)
    return Image.open(io.BytesIO(img))

def main():
    st.title("🖼️ Thumbnail Analyzer & Generator")
    st.write("Upload JPG/PNG thumbnails → GPT-4 Vision analyses → synthesize patterns → generate new thumbnail.")

    client = setup_openai_client()
    if not client:
        return

    if "data" not in st.session_state:
        st.session_state.data = []

    uploads = st.file_uploader("Upload thumbnails", type=["jpg","png","jpeg"], accept_multiple_files=True)
    if uploads:
        new = []
        for f in uploads:
            raw = f.read()
            if not any(d["name"]==f.name and d["size"]==len(raw) for d in st.session_state.data):
                new.append((f.name, raw))
        if new and st.button(f"Analyze {len(new)} New"):
            with st.spinner("Analyzing..."):
                for name, raw in new:
                    b64 = encode_b64(raw)
                    desc = analyze_image(client, b64, name)
                    st.session_state.data.append({"name":name,"size":len(raw),"desc":desc})
            st.success("Done.")

    if st.session_state.data:
        st.markdown("### Individual Analyses")
        for item in st.session_state.data:
            st.markdown(f"**{item['name']}**")
            with st.expander("View analysis"):
                st.write(item["desc"])

        if st.button("Synthesize & Generate"):
            with st.spinner("Synthesizing patterns..."):
                analyses = [d["desc"] for d in st.session_state.data]
                result = synthesize_patterns(client, analyses)
            st.subheader("Common Patterns & Psychology")
            st.write(result["analysis_summary"])
            st.subheader("Generated Thumbnail")
            thumb = generate_thumbnail(client, result["generation_prompt"])
            st.image(thumb, use_column_width=True)
            st.markdown(f"**Prompt:** `{result['generation_prompt']}`")

    st.sidebar.info("Uses only OpenAI: GPT-4 Vision for analysis & gpt_image_1 for generation.")

if __name__=="__main__":
    main()
