# app.py
import streamlit as st
import os, io, base64, json
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

def analyze_image(client, b64str, name):
    """
    Return JSON with just:
      - dominant_colors: [...color names...]
      - hooks: [...psychological hooks...]
    """
    sys = "You are an expert in marketing psychology."
    usr = (
        f"Image '{name}': extract ONLY two keys in JSON:\n"
        "  • dominant_colors: list of 3–5 color words\n"
        "  • hooks: list of 3–5 psychological techniques (urgency, curiosity…)\n"
        f"<IMAGE>data:image/jpeg;base64,{b64str}</IMAGE>"
    )
    r = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"system","content":sys}, {"role":"user","content":usr}],
        max_tokens=120
    )
    return json.loads(r.choices[0].message.content)

def synthesize(client, analyses):
    """
    From up to 5 of those tiny JSONs, return:
      - analysis_summary: list of 3 bullet-points
      - generation_prompt: single concise prompt
    """
    subset = analyses[-5:]
    prompt = (
        "You are an expert designer. Input = JSON array of objects "
        "with dominant_colors and hooks. "
        "Output ONLY valid JSON with:\n"
        "  analysis_summary: array of 3 summary bullets,\n"
        "  generation_prompt: one short text prompt to recreate that style."
    )
    r = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system","content":prompt},
            {"role":"user","content":json.dumps(subset)}
        ],
        max_tokens=200
    )
    return json.loads(r.choices[0].message.content)

def generate_image(client, prompt):
    resp = client.images.generate(
        model="gpt_image_1", prompt=prompt, size="1024x576", n=1
    )
    data = base64.b64decode(resp.data[0].b64_json)
    return Image.open(io.BytesIO(data))

def main():
    st.title("🖼️ Thumbnail Analyzer & Generator")
    client = get_client()
    if not client: return

    if "imgs" not in st.session_state:
        st.session_state.imgs = []  # each: {name, size, analysis}

    files = st.file_uploader("Upload JPG/PNG", accept_multiple_files=True)
    if files:
        new = []
        for f in files:
            raw = f.read()
            if not any(i["name"]==f.name and i["size"]==len(raw)
                       for i in st.session_state.imgs):
                new.append((f.name, raw))
        if new and st.button(f"Analyze {len(new)} New"):
            with st.spinner("Analyzing…"):
                for name, raw in new:
                    j = analyze_image(client, to_b64(raw), name)
                    st.session_state.imgs.append({
                        "name": name, "size": len(raw), "analysis": j
                    })
            st.success("Done.")

    if st.session_state.imgs:
        st.markdown("### Individual Results")
        for item in st.session_state.imgs:
            st.markdown(f"**{item['name']}**")
            st.json(item["analysis"])

        if st.button("Synthesize & Generate"):
            with st.spinner("Synthesizing…"):
                analyses = [i["analysis"] for i in st.session_state.imgs]
                result = synthesize(client, analyses)
            st.subheader("Common Patterns")
            for b in result["analysis_summary"]:
                st.write(f"- {b}")
            st.subheader("Generated Thumbnail")
            img = generate_image(client, result["generation_prompt"])
            st.image(img, use_column_width=True)
            st.markdown(f"**Prompt:** `{result['generation_prompt']}`")

    st.sidebar.info("Uses only OpenAI: GPT-4 Vision → tiny JSON → gpt_image_1")

if __name__ == "__main__":
    main()
