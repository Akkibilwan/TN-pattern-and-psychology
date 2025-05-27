# app.py
import streamlit as st
import os, io, base64
from PIL import Image
import openai

st.set_page_config(page_title="Thumbnail Analyzer", layout="wide")

def get_client():
    key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        key = st.sidebar.text_input("OpenAI API Key", type="password")
    if not key:
        st.sidebar.error("API key required.")
        return None
    return openai.OpenAI(api_key=key)

def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode()

def analyze_image(client, b64str: str, name: str) -> str:
    """
    Returns plain-text analysis:
      • Dominant Colors: red, blue…
      • Psychological Hooks: urgency, curiosity…
    """
    sys = "You are an expert in visual communication and marketing psychology."
    usr = (
        f"Analyze image '{name}'.\n"
        "Provide TWO bullet lists, plain text only:\n"
        "- Dominant Colors (3–5 color names)\n"
        "- Psychological Hooks (3–5 techniques: urgency, curiosity, etc.)\n"
        f"<IMAGE_DATA>data:image/jpeg;base64,{b64str}</IMAGE_DATA>"
    )
    r = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"system","content":sys}, {"role":"user","content":usr}],
        max_tokens=150
    )
    return r.choices[0].message.content.strip()

def synthesize(client, analyses: list[str]) -> str:
    """
    Takes the plain-text analyses, and returns:
      • 3 bullets summarizing common patterns & hooks
      • A single line starting with "Image Prompt:" for generation
    """
    # only keep the last 5 analyses to stay small
    recent = analyses[-5:]
    joined = "\n\n".join(f"Analysis #{i+1}:\n{a}" for i,a in enumerate(recent))
    sys = "You are an expert in marketing psychology and design."
    usr = (
        "Given these analyses, in plain text:\n"
        "1) Summarize the COMMON visual patterns & psychological hooks in 3 bullet points.\n"
        "2) Then on its own line, write:\n"
        "   Image Prompt: <your concise prompt to recreate that style>\n\n"
        f"{joined}"
    )
    r = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"system","content":sys}, {"role":"user","content":usr}],
        max_tokens=200
    )
    return r.choices[0].message.content.strip()

def generate_image(client, prompt: str) -> Image.Image:
    resp = client.images.generate(
        model="gpt_image_1", prompt=prompt, size="1024x576", n=1
    )
    data = base64.b64decode(resp.data[0].b64_json)
    return Image.open(io.BytesIO(data))

def main():
    st.title("🖼️ Thumbnail Analyzer & Generator")
    st.write("1. Upload thumbnails → 2. Analyze bullets → 3. Synthesize bullets & prompt → 4. Generate image")

    client = get_client()
    if not client:
        return

    if "items" not in st.session_state:
        st.session_state.items = []  # each is {name, size, analysis}

    files = st.file_uploader("Upload JPG/PNG", accept_multiple_files=True)
    if files:
        to_process = []
        for f in files:
            raw = f.read()
            if not any(i["name"]==f.name and i["size"]==len(raw) for i in st.session_state.items):
                to_process.append((f.name, raw))
        if to_process and st.button(f"Analyze {len(to_process)} New"):
            with st.spinner("Analyzing…"):
                for name, raw in to_process:
                    b64str = to_b64(raw)
                    analysis = analyze_image(client, b64str, name)
                    st.session_state.items.append({"name":name,"size":len(raw),"analysis":analysis})
            st.success("Analysis done.")

    if st.session_state.items:
        st.markdown("### Individual Analyses")
        for it in st.session_state.items:
            st.markdown(f"**{it['name']}**")
            st.write(it["analysis"])

        if st.button("Synthesize & Generate"):
            with st.spinner("Synthesizing…"):
                texts = [it["analysis"] for it in st.session_state.items]
                synthesis = synthesize(client, texts)
            st.subheader("Common Patterns & Hooks")
            st.write("\n".join(synthesis.split("\n")[:-1]))  # all lines except the last
            prompt_line = synthesis.split("\n")[-1]
            st.subheader("Generated Thumbnail")
            thumb = generate_image(client, prompt_line.replace("Image Prompt:","").strip())
            st.image(thumb, use_column_width=True)
            st.markdown(f"**{prompt_line}**")

    st.sidebar.info("Uses only OpenAI: GPT-4 Vision for analysis & gpt_image_1 for generation.")

if __name__ == "__main__":
    main()
