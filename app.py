import streamlit as st
import openai
import re
import json
import base64

# —————————————————————————————————————————————————————————————
# CONFIG
# —————————————————————————————————————————————————————————————
# Use your new OpenAI Python v1.x interface:
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(
    page_title="Thumbnail Analyzer & Prompt Generator",
    layout="wide"
)
st.title("📸 Thumbnail Analyzer & Prompt-to-Image Generator")

# —————————————————————————————————————————————————————————————
# HELPER: GPT-4o VISION ANALYSIS (new v1.x calls)
# —————————————————————————————————————————————————————————————
def analyze_with_gpt_vision(img_bytes: bytes, filename: str) -> str:
    """
    Sends a base64-embedded image to GPT-4o Vision and returns
    its raw JSON-style response as text.
    """
    # 1) Encode as data URL
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    data_url = f"data:image/png;base64,{b64}"

    # 2) Build the multimodal messages
    system = {
        "role": "system",
        "content": (
            "You are an expert in visual communication, marketing psychology, and digital design.\n"
            "Respond *only* with a single JSON object—no markdown or extra text."
        ),
    }
    user = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": (
                    "Analyze this YouTube thumbnail and output JSON with exactly these keys:\n"
                    "  • visual_breakdown: a list of key visual elements\n"
                    "  • psychology: the primary attention-grabbing tactics\n"
                    "  • pattern: the overall design pattern or layout\n\n"
                    "Example:\n"
                    "```json\n"
                    "{\n"
                    '  "visual_breakdown": ["bold text", "high-contrast colors"],\n'
                    '  "psychology": "curiosity gap by showing partial info",\n'
                    '  "pattern": "text on left, face on right"\n'
                    "}\n"
                    "```"
                )
            },
            {"type": "image_url", "image_url": {"url": data_url}}
        ],
        "name": filename
    }

    # NEW v1.x call:
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[system, user],
        max_tokens=500
    )
    return resp.choices[0].message.content

# —————————————————————————————————————————————————————————————
# 1) UPLOAD
# —————————————————————————————————————————————————————————————
uploaded_files = st.file_uploader(
    "Upload one or more thumbnail images",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Please upload at least one thumbnail to get started.")
    st.stop()

# —————————————————————————————————————————————————————————————
# 2) ANALYZE EACH WITH GPT-4o VISION
# —————————————————————————————————————————————————————————————
analyses = []

for img_file in uploaded_files:
    st.subheader(f"Analysis for: {img_file.name}")
    st.image(img_file, use_column_width=True)

    img_bytes = img_file.read()
    raw = analyze_with_gpt_vision(img_bytes, img_file.name)

    st.write("🔍 Raw GPT-Vision response:")
    st.code(raw, language="")

    # Extract first JSON object
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        st.error("⚠️ No JSON object found in the response.")
        continue
    json_str = raw[start:end]

    # Remove any trailing commas before } or ]
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

    # Parse or show error
    try:
        analysis = json.loads(json_str)
    except json.JSONDecodeError as e:
        st.error(f"🛑 JSON parsing failed: {e}")
        st.code(json_str, language="json")
        continue

    analyses.append({
        "file": img_file.name,
        "visual_breakdown": analysis.get("visual_breakdown", []),
        "psychology": analysis.get("psychology", ""),
        "pattern": analysis.get("pattern", "")
    })
    st.json(analysis)

# —————————————————————————————————————————————————————————————
# 3) SYNTHESIZE COMMON PATTERNS & PSYCHOLOGIES
# —————————————————————————————————————————————————————————————
st.markdown("---")
st.header("✨ Common Patterns & Psychological Strategies")

patterns = sorted({a["pattern"] for a in analyses if a["pattern"]})
psychologies = sorted({a["psychology"] for a in analyses if a["psychology"]})

st.write("**Patterns:**", patterns or "None detected")
st.write("**Psychologies:**", psychologies or "None detected")

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
    "Use these thumbnail analyses to craft a single prompt for GPT-4o Vision that reproduces "
    "the visual patterns and psychological hooks when generating a new image:\n\n"
    + combined
)
st.code(default_template, language="markdown")

custom_prompt = st.text_area(
    "✏️ Customize or copy this prompt for image generation:",
    value=default_template,
    height=200
)

# —————————————————————————————————————————————————————————————
# 5) GENERATE SAMPLE THUMBNAIL (using gpt_image_1)
# —————————————————————————————————————————————————————————————
if st.button("Generate Sample Thumbnail"):
    if not custom_prompt.strip():
        st.error("Please enter a non-empty prompt above.")
    else:
        with st.spinner("Generating with gpt_image_1…"):
            img_resp = openai.images.generate(
                model="gpt_image_1",
                prompt=custom_prompt,
                n=1,
                size="1024x1024"
            )
            url = img_resp.data[0].url
            st.image(url, caption="🎨 Generated Thumbnail")

# —————————————————————————————————————————————————————————————
# 6) READY-TO-USE VISUAL-BREAKDOWN PROMPT
# —————————————————————————————————————————————————————————————
st.markdown("---")
st.header("🔧 Ready-to-Use Visual-Breakdown Prompt")

breakdown_prompt = (
    "You are an expert in visual communication, marketing psychology, and digital design.\n"
    "Analyze a set of thumbnail images and structure your output under these headings:\n\n"
    "1. Visual Elements Breakdown\n"
    "2. Psychological Impact & Attention-Grabbing Techniques\n"
    "3. Emotional Resonance\n"
    "4. Intrigue & Narrative\n"
    "5. Overall Pattern & Strategy Synthesis\n\n"
    "Respond *only* with JSON."
)
st.code(breakdown_prompt, language="markdown")
