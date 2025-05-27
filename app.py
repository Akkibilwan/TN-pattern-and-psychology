# app.py
import streamlit as st
import os
import io
import base64
import json
from PIL import Image
import openai

# --- Config ---
st.set_page_config(page_title="Thumbnail Analyzer", layout="wide")

def get_openai_client():
    key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        key = st.sidebar.text_input("OpenAI API Key", type="password")
    if not key:
        st.sidebar.error("API key required.")
        return None
    return openai.OpenAI(api_key=key)

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()

def analyze_image(client, b64str: str, name: str) -> dict:
    """
    Returns a small JSON with exactly these keys:
      - dominant_colors: [“red”,…]
      - hooks: [“urgency”,…]
      - composition: short str
      - text_style: short str
      - mood: short str
    """
    system = (
        "You are an expert in visual communication and marketing psychology. "
        "Given an image, output JSON with exactly these 5 keys: "
        "dominant_colors (array of color words), hooks (array of psychological hooks), "
        "composition (string), text_style (string), mood (string)."
    )
    user = (
        f"Analyze '{name}'. Respond ONLY with JSON."
        f"<IMAGE_DATA>data:image/jpeg;base64,{b64str}</IMAGE_DATA>"
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        max_tokens=250
    )
    return json.loads(resp.choices[0].message.content)

def synthesize(client, analyses: list[dict]) -> dict:
    """
    Given a list of at most 5 analysis-JSONs, produce:
      - analysis_summary: numbered bullet summary
      - generation_prompt: a single prompt string
    Returned as JSON.
    """
    subset = analyses[-5:]
    prompt = (
        "You are an expert in design & marketing psychology. "
        "Input is a JSON array of analysis objects (dominant_colors, hooks, composition, text_style, mood). "
        "1) Summarize common visual patterns & psychological strategies in 3–5 bullets. "
        "2) Write one concise image-generation prompt to recreate that style. "
        "Output ONLY valid JSON with keys analysis_summary (array of strings) and generation_prompt (string)."
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system", "content": prompt},
            {"role":"user",   "content": json.dumps(subset)},
        ],
        max_tokens=400
    )
    return json.loads(resp.choices[0].message.content)

def generate_image(client, prompt: str) -> Image.Image:
    resp = client.images.generate(
        model="gpt_image_1",
        prompt=prompt,
        size="1024x576",
        n=1
    )
    data = base64.b64decode(resp.data[0].b64_json)
    return Image.open(io.BytesIO(data))

# --- UI ---
def main():
    st.title("🖼️ Thumbnail Analyzer & Generator")
    client = get_openai_client()
    if not client:
        return

    if "imgs" not in st.session_state:
        st.session_state.imgs = []  # each is {name, data, analysis}

    uploaded = st.file_uploader("JPG/PNG thumbnails", accept_multiple_files=True)
    if uploaded:
        new = []
        for f in uploaded:
            raw = f.read()
            if not any(i["name"]==f.name and i["size"]==len(raw) for i in st.session_state.imgs):
                new.append((f.name, raw))
        if new and st.button(f"Analyze {len(new)} new"):
            with st.spinner("Analyzing…"):
                for name, data in new:
                    j = analyze_image(client, b64(data), name)
                    st.session_state.imgs.append({
                        "name": name,
                        "size": len(data),
                        "analysis": j
                    })
            st.success("Done.")

    if st.session_state.imgs:
        st.markdown("### Individual Analyses")
        for item in st.session_state.imgs:
            st.markdown(f"**{item['name']}**")
            st.json(item["analysis"])

        if st.button("Synthesize & Generate"):
            with st.spinner("Synthesizing…"):
                analyses = [i["analysis"] for i in st.session_state.imgs]
                result = synthesize(client, analyses)
            st.subheader("Common Patterns & Psychology")
            for idx, bullet in enumerate(result["analysis_summary"], 1):
                st.write(f"{idx}. {bullet}")
            st.subheader("🔮 Generated Thumbnail")
            img = generate_image(client, result["generation_prompt"])
            st.image(img, use_column_width=True)
            st.markdown(f"**Prompt:** `{result['generation_prompt']}`")

    st.sidebar.info("Uses only OpenAI: GPT-4 Vision → JSON analysis → synthesize → gpt_image_1")

if __name__ == "__main__":
    main()
