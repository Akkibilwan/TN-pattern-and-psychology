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

def analyze_image(client, b64str: str, name: str) -> dict:
    """
    Uses GPT-4 Vision via a structured image_url part.
    Returns JSON with just:
      • dominant_colors: [...]
      • hooks: [...]
    """
    system = "You are an expert in marketing psychology. Respond ONLY with JSON."
    user_content = [
        {"type": "text", "text": f"Image '{name}': extract two keys:"},
        {"type": "text", "text": "• dominant_colors: list 3–5 color names"},
        {"type": "text", "text": "• hooks: list 3–5 psychological techniques"},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64str}"}}
    ]
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system","content":system},
            {"role":"user","content":user_content}
        ],
        max_tokens=100
    )
    text = resp.choices[0].message.content
    try:
        parsed = json.loads(text)
        return {
            "dominant_colors": parsed.get("dominant_colors", []),
            "hooks":          parsed.get("hooks", [])
        }
    except json.JSONDecodeError:
        st.warning(f"Couldn't parse JSON for '{name}'.")
        return {"dominant_colors": [], "hooks": []}

def synthesize(client, items: list[dict]) -> dict:
    """
    From up to 5 of those tiny JSONs, return:
      • analysis_summary: [3 bullets…]
      • generation_prompt: "…"
    """
    subset = items[-5:]
    prompt = (
        "You are a design-and-psychology expert.\n"
        "Input=JSON array with objects {dominant_colors, hooks}.\n"
        "Output ONLY valid JSON with:\n"
        "  analysis_summary: array of 3 summary bullets,\n"
        "  generation_prompt: single concise prompt to recreate that style.\n"
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system","content":prompt},
            {"role":"user","content":json.dumps(subset)}
        ],
        max_tokens=200
    )
    text = resp.choices[0].message.content
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        st.warning("Failed to parse synthesis JSON.")
        return {"analysis_summary":[text], "generation_prompt":text}

def generate_image(client, prompt: str) -> Image.Image:
    resp = client.images.generate(
        model="gpt_image_1",
        prompt=prompt,
        size="1024x576",
        n=1
    )
    img_data = base64.b64decode(resp.data[0].b64_json)
    return Image.open(io.BytesIO(img_data))

def main():
    st.title("🖼️ Thumbnail Analyzer & Generator")
    client = get_client()
    if not client:
        return

    if "imgs" not in st.session_state:
        st.session_state.imgs = []

    uploads = st.file_uploader("Upload JPG/PNG thumbnails", accept_multiple_files=True)
    if uploads:
        new = []
        for f in uploads:
            raw = f.read()
            if not any(i["name"]==f.name and i["size"]==len(raw)
                       for i in st.session_state.imgs):
                new.append((f.name, raw))
        if new and st.button(f"Analyze {len(new)} New"):
            with st.spinner("Analyzing…"):
                for name, raw in new:
                    j = analyze_image(client, to_b64(raw), name)
                    st.session_state.imgs.append({
                        "name": name,
                        "size": len(raw),
                        "analysis": j
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
            thumb = generate_image(client, result["generation_prompt"])
            st.image(thumb, use_column_width=True)
            st.markdown(f"**Prompt:** `{result['generation_prompt']}`")

    st.sidebar.info("Uses only OpenAI: GPT-4 Vision for analysis, gpt_image_1 for generation.")

if __name__ == "__main__":
    main()
