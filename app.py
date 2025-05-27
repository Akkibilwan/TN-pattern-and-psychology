# app.py
import streamlit as st
import os, io, base64, json
from PIL import Image
import openai

# ——— Page config —————————————————————————————————————————————————————————
st.set_page_config(page_title="Thumbnail Insights & Wireframe Generator", layout="wide")

# ——— Helpers —————————————————————————————————————————————————————————————
def get_openai_client():
    key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        key = st.sidebar.text_input("OpenAI API Key", type="password")
    if not key:
        st.sidebar.error("🔑 API key required")
        return None
    return openai.OpenAI(api_key=key)

def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode()

# ——— 1) Per-thumbnail analysis ——————————————————————————————————————————————
def analyze_thumbnail(client, b64str: str, name: str) -> dict:
    """
    Returns a JSON with:
      - patterns: 3–5 short phrases describing visual patterns
      - psychology: 3–5 short phrases describing psychological strategies
      - pros: 3 reasons why this thumbnail would work on YouTube
      - cons: 3 reasons why it might NOT work
    """
    system = "You are an expert in visual communication and marketing psychology. Respond ONLY with JSON."
    user_content = [
        {"type": "text", "text": f"Thumbnail '{name}': extract exactly four keys in JSON:"},
        {"type": "text", "text": "• patterns: list 3–5 visual patterns (e.g., ‘bold text overlay’, ‘rule of thirds’)."},
        {"type": "text", "text": "• psychology: list 3–5 psychological hooks (e.g., ‘urgency’, ‘curiosity’)."},
        {"type": "text", "text": "• pros: list 3 reasons why this would perform well on YouTube."},
        {"type": "text", "text": "• cons: list 3 reasons why it might underperform."},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64str}"}}
    ]
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content},
        ],
        max_tokens=250
    )
    text = resp.choices[0].message.content
    try:
        parsed = json.loads(text)
        # Ensure keys exist
        return {
            "patterns":      parsed.get("patterns", []),
            "psychology":    parsed.get("psychology", []),
            "pros":          parsed.get("pros", []),
            "cons":          parsed.get("cons", [])
        }
    except json.JSONDecodeError:
        st.warning(f"⚠️ Failed to parse analysis JSON for '{name}'.")
        return {"patterns":[], "psychology":[], "pros":[], "cons":[]}

# ——— 2) Synthesize common insights & build wireframe prompt ——————————————————————
def synthesize_insights(client, analyses: list[dict]) -> dict:
    """
    From up to 5 per-thumbnail JSONs, returns JSON with:
      - common_patterns: 3 bullet-points
      - common_psychology: 3 bullet-points
      - wireframe_prompt: a concise prompt to generate a thumbnail wireframe capturing those patterns & psychology
    """
    subset = analyses[-5:]
    system = "You are a design and marketing-psychology expert. Respond ONLY with JSON."
    user_text = (
        "Input = JSON array of objects with keys patterns, psychology, pros, cons.\n"
        "1) common_patterns: list 3 top visual patterns shared across thumbnails.\n"
        "2) common_psychology: list 3 top psychological hooks shared.\n"
        "3) wireframe_prompt: one short prompt for an AI to generate a simple thumbnail WIREFRAME using those patterns & psychology."
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system","content":system},
            {"role":"user","content":user_text},
            {"role":"assistant","content":""},  # few-shot blank
            {"role":"user","content":json.dumps(subset)}
        ],
        max_tokens=300
    )
    text = resp.choices[0].message.content
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        st.warning("⚠️ Failed to parse synthesis JSON.")
        return {
            "common_patterns":   [],
            "common_psychology": [],
            "wireframe_prompt":  text
        }

# ——— 3) Generate the wireframe image ——————————————————————————————————————————
def generate_wireframe(client, prompt: str) -> Image.Image:
    resp = client.images.generate(
        model="gpt_image_1",
        prompt=prompt,
        size="1024x576",
        n=1
    )
    img_bytes = base64.b64decode(resp.data[0].b64_json)
    return Image.open(io.BytesIO(img_bytes))

# ——— Streamlit UI —————————————————————————————————————————————————————
def main():
    st.title("🖼️ Thumbnail Insights & Wireframe Generator")
    st.markdown(
        "1. Upload related thumbnails  "
        "2. Analyze each for patterns, psychology, pros/cons  "
        "3. Synthesize common insights  "
        "4. Generate a wireframe image based on those insights"
    )

    client = get_openai_client()
    if not client:
        return

    if "data" not in st.session_state:
        st.session_state.data = []  # list of {name, size, analysis}

    uploads = st.file_uploader("Upload JPG/PNG thumbnails", accept_multiple_files=True)
    if uploads:
        new = []
        for f in uploads:
            raw = f.read()
            if not any(d["name"]==f.name and d["size"]==len(raw) for d in st.session_state.data):
                new.append((f.name, raw))
        if new and st.button(f"Analyze {len(new)} New"):
            with st.spinner("Analyzing thumbnails…"):
                for name, raw in new:
                    analysis = analyze_thumbnail(client, to_b64(raw), name)
                    st.session_state.data.append({
                        "name":     name,
                        "size":     len(raw),
                        "analysis": analysis
                    })
            st.success("Analysis complete!")

    if st.session_state.data:
        st.markdown("### 1. Individual Analyses")
        for item in st.session_state.data:
            st.markdown(f"**{item['name']}**")
            st.write("- **Patterns:**", ", ".join(item["analysis"]["patterns"]))
            st.write("- **Psychology:**", ", ".join(item["analysis"]["psychology"]))
            st.write("- **Pros:**", ", ".join(item["analysis"]["pros"]))
            st.write("- **Cons:**", ", ".join(item["analysis"]["cons"]))
            st.markdown("---")

        if st.button("2. Synthesize & Generate Wireframe"):
            with st.spinner("Synthesizing insights…"):
                analyses = [d["analysis"] for d in st.session_state.data]
                result = synthesize_insights(client, analyses)

            st.subheader("### 2. Common Insights")
            st.write("**Common Patterns:**")
            for p in result.get("common_patterns", []):
                st.write(f"- {p}")
            st.write("**Common Psychology:**")
            for psy in result.get("common_psychology", []):
                st.write(f"- {psy}")

            st.subheader("### 3. Generated Wireframe")
            wire = generate_wireframe(client, result.get("wireframe_prompt",""))
            st.image(wire, use_column_width=True)
            st.markdown(f"**Wireframe Prompt:**\n```\n{result.get('wireframe_prompt','')}\n```")

    st.sidebar.info(
        "Uses GPT-4 Vision to analyze thumbnails, then GPT-4 to synthesize insights,\n"
        "and gpt_image_1 to generate a simple wireframe image."
    )

if __name__ == "__main__":
    main()
