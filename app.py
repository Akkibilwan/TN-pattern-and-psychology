import streamlit as st
import openai
import re
import json

# —————————————————————————————————————————————————————————————
# CONFIG
# —————————————————————————————————————————————————————————————
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(
    page_title="Thumbnail Analyzer & Prompt Generator",
    layout="wide"
)
st.title("📸 Thumbnail Analyzer & Prompt-to-Image Generator")

# —————————————————————————————————————————————————————————————
# 1) UPLOAD
# —————————————————————————————————————————————————————————————
uploaded_files = st.file_uploader(
    "Upload one or more thumbnail images",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Start by uploading at least one thumbnail above.")
    st.stop()

# —————————————————————————————————————————————————————————————
# 2) ANALYZE EACH VIA GPT-4o VISION
# —————————————————————————————————————————————————————————————
analyses = []
for img_file in uploaded_files:
    st.subheader(f"Analysis for: {img_file.name}")
    st.image(img_file, use_column_width=True)

    img_bytes = img_file.read()

    system_prompt = (
        "You are an expert in visual communication, marketing psychology, and digital design.  "
        "Respond *only* with a single JSON object – no markdown or extra text."
    )
    user_prompt = (
        "Analyze this thumbnail and return a JSON object with exactly these keys:\n"
        "  • visual_breakdown (list of key visual elements),\n"
        "  • psychology (the attention-grabbing tactics),\n"
        "  • pattern (the overall design pattern).\n\n"
        "Example:\n"
        "```json\n"
        "{\n"
        '  "visual_breakdown": ["bold text", "high-contrast colors"],\n'
        '  "psychology": "curiosity gap by showing partial info",\n'
        '  "pattern": "text on left, face on right"\n'
        "}\n"
        "```"
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt, "name": img_file.name}
        ],
        files=[{
            "file": img_bytes,
            "filename": img_file.name,
            "content_type": img_file.type
        }]
    )

    raw = resp.choices[0].message.content
    st.write("🔍 Raw GPT response:")
    st.code(raw, language="")

    # ————————————————— Extract JSON via naive find —————————————————
    text_response = raw.strip()
    json_start = text_response.find("{")
    json_end = text_response.rfind("}") + 1
    if json_start != -1 and json_end != -1:
        json_str = text_response[json_start:json_end]
    else:
        json_str = raw

    # Optional: remove trailing commas before ] or }
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

    # —————————————————————————————————————————————————————————————
    # PARSE or SHOW ERROR
    # —————————————————————————————————————————————————————————————
    try:
        analysis = json.loads(json_str)
    except json.JSONDecodeError as e:
        st.error(f"🛑 JSON parsing failed: {e}")
        st.code(json_str, language="json")
        continue

    analyses.append({"file": img_file.name, **analysis})
    st.json(analysis)

# —————————————————————————————————————————————————————————————
# 3) SYNTHESIZE COMMON PATTERNS & PSYCHOLOGY
# —————————————————————————————————————————————————————————————
st.markdown("---")
st.header("✨ Common Patterns & Psychological Strategies")

patterns = [a["pattern"] for a in analyses if "pattern" in a]
psychologies = [a["psychology"] for a in analyses if "psychology" in a]

st.write(f"**Patterns:** {sorted(set(patterns))}")
st.write(f"**Psychologies:** {sorted(set(psychologies))}")

# —————————————————————————————————————————————————————————————
# 4) AUTO-GENERATE A PROMPT TEMPLATE
# —————————————————————————————————————————————————————————————
st.markdown("---")
st.header("📝 Auto-Generated Prompt Template")

combined = "\n\n".join(
    f"File: {a['file']}\nPattern: {a['pattern']}\nPsychology: {a['psychology']}"
    for a in analyses
)
default_template = (
    "Use the following thumbnail analyses to craft a single prompt for GPT-4o-vision that would "
    "reproduce these visual patterns and psychological hooks when generating a new image:\n\n"
    + combined
)
st.code(default_template, language="markdown")

custom_prompt = st.text_area(
    "✏️ Customize or copy this prompt for image generation:",
    value=default_template,
    height=200
)

# —————————————————————————————————————————————————————————————
# 5) GENERATE A SAMPLE THUMBNAIL (gpt_image_1)
# —————————————————————————————————————————————————————————————
if st.button("Generate Sample Thumbnail"):
    if not custom_prompt.strip():
        st.error("Please supply a non-empty prompt above.")
    else:
        with st.spinner("Generating with gpt_image_1…"):
            img_resp = openai.Image.create(
                model="gpt_image_1",
                prompt=custom_prompt,
                n=1,
                size="1024x1024"
            )
            url = img_resp.data[0].url
            st.image(url, caption="🎨 Generated Thumbnail")

# —————————————————————————————————————————————————————————————
# 6) VISUAL BREAKDOWN PROMPT FOR FUTURE USE
# —————————————————————————————————————————————————————————————
st.markdown("---")
st.header("🔧 Ready-to-Use Visual-Breakdown Prompt")

breakdown_prompt = (
    "You are an expert in visual communication, marketing psychology, and digital design.  "
    "Analyze a set of thumbnail images and structure your output under these headings:\n\n"
    "1. Visual Elements Breakdown\n"
    "2. Psychological Impact & Attention-Grabbing Techniques\n"
    "3. Emotional Resonance\n"
    "4. Intrigue & Narrative\n"
    "5. Overall Pattern & Strategy Synthesis\n\n"
    "Respond *only* with JSON."
)
st.code(breakdown_prompt, language="markdown")
