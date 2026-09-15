"""
🤖 Bemo — AI Companion (Streamlit Edition)
==========================================
A web port of the original Tkinter desktop notebook (Bemo_chatbot_v3.ipynb).

Same brain, new body:
  • Gemini 2.5 Flash model + personality prompt
  • Tools: web search (DDG), calculator (sympy), weather (wttr.in), date/time
  • File understanding: PDF · DOCX · PPTX · XLSX · TXT · images
  • Camera capture (via st.camera_input) with vision analysis
  • Voice input (via st.audio_input, needs Streamlit >= 1.36) + Google speech recognition
  • Voice output (spoken in your browser using the Web Speech API — no server TTS needed)
  • Rolling memory of the last 15 turns

Run it:
    pip install -r requirements.txt
    streamlit run bemo_streamlit_app.py

You'll need a free Gemini API key: https://aistudio.google.com/apikey
(paste it in the sidebar, or set the GOOGLE_API_KEY environment variable)

Optional: drop the included `streamlit_config.toml` into a `.streamlit/config.toml`
file next to this script for a matching dark theme.
"""

import os
import re
import time

import streamlit as st
import streamlit.components.v1 as components

# ============================================================================
# PAGE SETUP
# ============================================================================
st.set_page_config(page_title="Bemo — AI Companion", page_icon="🤖", layout="centered")

FILE_ICONS = {
    ".pdf": "📕", ".docx": "📘", ".pptx": "📙",
    ".xlsx": "📗", ".xls": "📗", ".xlsm": "📗",
    ".jpg": "🖼️", ".jpeg": "🖼️", ".png": "🖼️",
    ".gif": "🖼️", ".webp": "🖼️", ".bmp": "🖼️",
    ".txt": "📄", ".md": "📄", ".py": "🐍", ".csv": "📊",
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
MAX_MEMORY = 15

FILE_QUESTION_KW = {
    "explain", "summarize", "what", "tell", "describe",
    "اشرح", "لخص", "ايه", "ما", "وضح",
    "e7ki", "e2ra", "wad7li", "shoof", "2olly",
}

# ============================================================================
# SESSION STATE
# ============================================================================
defaults = {
    "messages": [],
    "memory": [],
    "file_context": {"name": None, "content": None},
    "last_uploaded_id": None,
    "last_camera_hash": None,
    "last_audio_hash": None,
    "last_spoken_idx": -1,
    "pending_prompt": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ============================================================================
# SIDEBAR — API KEY
# ============================================================================
with st.sidebar:
    st.markdown("## 🤖 Bemo")
    st.caption("Multilingual AI companion · Arabic · English · Français · Franco")
    api_key = st.text_input(
        "Google (Gemini) API key",
        type="password",
        value=os.getenv("GOOGLE_API_KEY", ""),
        help="Get one free at https://aistudio.google.com/apikey",
    )

if not api_key:
    st.info("👋 Enter your Google Gemini API key in the sidebar to start chatting with Bemo.")
    st.stop()

import google.generativeai as genai

genai.configure(api_key=api_key)


@st.cache_resource(show_spinner=False)
def get_model():
    return genai.GenerativeModel("gemini-2.5-flash")


model = get_model()

# ============================================================================
# RATE-LIMIT-AWARE GENERATION (mirrors the notebook's _ModelWrapper)
# ============================================================================
def safe_generate(content, status_placeholder=None):
    max_attempts = 5
    wait = 20
    for attempt in range(1, max_attempts + 1):
        try:
            return model.generate_content(content)
        except Exception as e:
            msg = str(e)
            match = re.search(r"retry[^\d]*(\d+)", msg, re.I)
            suggested = int(match.group(1)) + 2 if match else wait
            if "429" in msg or "quota" in msg.lower():
                if attempt == max_attempts:
                    raise
                for s in range(suggested, 0, -1):
                    if status_placeholder is not None:
                        status_placeholder.info(
                            f"⏳ Rate limit — retrying in {s}s "
                            f"(attempt {attempt}/{max_attempts - 1})…"
                        )
                    time.sleep(1)
                wait = min(wait * 2, 120)
            else:
                raise


# ============================================================================
# TOOLS — web search · calculator · weather · date/time
# ============================================================================
def web_search(query: str) -> str:
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=4):
                results.append(r.get("body", ""))
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search unavailable: {e}"


def calculator(query: str) -> str:
    import sympy as sp
    expr = re.sub(r"[^0-9+\-*/().^ %]", " ", query).strip()
    try:
        return str(sp.sympify(expr))
    except Exception:
        return "Error: couldn't parse the expression."


def get_weather(city_query: str) -> str:
    import requests
    m = re.search(
        r"(?:weather|طقس|جو|ta2s|t2s|gaw|clima|7arara)\s+(?:in|في|ف|fe|f)?\s*(\w+)",
        city_query, re.I,
    )
    city = m.group(1) if m else city_query.split()[-1]
    try:
        return requests.get(f"https://wttr.in/{city}?format=3", timeout=5).text
    except Exception:
        return "Weather service unavailable."


def get_datetime(_=None) -> str:
    from datetime import datetime
    now = datetime.now()
    return now.strftime("📅 %A, %d %B %Y  |  🕐 %I:%M %p")


WEATHER_KW = {
    "weather", "طقس", "جو", "حرارة", "درجة", "temperature", "forecast",
    "ta2s", "t2s", "gaw", "7arara", "clima",
}
DATETIME_KW = {
    "time", "date", "وقت", "تاريخ", "النهارده", "today", "اليوم",
    "الساعة", "now", "clock", "day", "month", "year",
    "sa3a", "yom", "ennaharda", "el-yom", "elsa3a",
}
CALC_KW = {
    "calc", "calculate", "حساب", "احسب", "يساوي", "equals", "compute",
    "e7seb", "7esab", "yesawi",
}
TOOLS = {"SEARCH", "CALCULATE", "WEATHER", "DATETIME", "NONE"}
TOOL_FN = {
    "SEARCH": web_search,
    "CALCULATE": calculator,
    "WEATHER": get_weather,
    "DATETIME": get_datetime,
}


def fast_decide(text: str):
    low = text.lower()
    words = set(low.split())
    if words & WEATHER_KW:
        return "WEATHER"
    if words & DATETIME_KW:
        return "DATETIME"
    if words & CALC_KW:
        return "CALCULATE"
    math_chars = sum(1 for c in text if c in "0123456789+-*/().^ ")
    if math_chars / max(len(text), 1) > 0.55:
        return "CALCULATE"
    return None


def decide_tool(user_input: str, status_placeholder=None) -> str:
    quick = fast_decide(user_input)
    if quick:
        return quick
    prompt = (
        "Reply with ONE word only — SEARCH, CALCULATE, WEATHER, DATETIME, or NONE.\n"
        "SEARCH only if real-time/factual web data is needed.\n"
        f"Question: {user_input}"
    )
    res = safe_generate(prompt, status_placeholder)
    dec = res.text.strip().upper()
    for t in TOOLS:
        if t in dec:
            return t
    return "NONE"


# ============================================================================
# FILE READING — PDF · DOCX · PPTX · XLSX · TXT · images
# ============================================================================
def _read_pdf(file_obj) -> str:
    from pypdf import PdfReader
    reader = PdfReader(file_obj)
    text, char_budget = [], 12_000
    for page in reader.pages:
        chunk = page.extract_text() or ""
        text.append(chunk)
        char_budget -= len(chunk)
        if char_budget <= 0:
            break
    return "\n".join(text)[:12_000]


def _read_docx(file_obj) -> str:
    import docx
    doc = docx.Document(file_obj)
    parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            parts.append("\t".join(c.text for c in row.cells))
    return "\n".join(parts)[:12_000]


def _read_pptx(file_obj) -> str:
    from pptx import Presentation
    prs = Presentation(file_obj)
    parts = []
    for i, slide in enumerate(prs.slides, 1):
        parts.append(f"\n--- Slide {i} ---")
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                parts.append(shape.text.strip())
    return "\n".join(parts)[:12_000]


def _read_xlsx(file_obj) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    parts = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        parts.append(f"\n--- Sheet: {sheet_name} ---")
        for row in ws.iter_rows(max_row=80, values_only=True):
            row_str = "\t".join(str(c) if c is not None else "" for c in row)
            if row_str.strip():
                parts.append(row_str)
    return "\n".join(parts)[:12_000]


def read_file_content(uploaded_file):
    """Return (text_content, is_image). For images returns (None, True)."""
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    try:
        if ext == ".pdf":
            return _read_pdf(uploaded_file), False
        elif ext == ".docx":
            return _read_docx(uploaded_file), False
        elif ext == ".pptx":
            return _read_pptx(uploaded_file), False
        elif ext in (".xlsx", ".xls", ".xlsm"):
            return _read_xlsx(uploaded_file), False
        elif ext in IMAGE_EXTS:
            return None, True
        else:
            return uploaded_file.read().decode("utf-8", errors="ignore")[:12_000], False
    except Exception as e:
        return f"[Error reading file: {e}]", False


def summarize_file(uploaded_file, status_placeholder=None) -> str:
    """Summarize any supported file. Stores content for follow-up questions."""
    from PIL import Image

    fname = uploaded_file.name
    ext = os.path.splitext(fname)[1].lower()
    content, is_image = read_file_content(uploaded_file)

    if is_image:
        try:
            img = Image.open(uploaded_file)
            q = "Describe this image in detail. What do you see?"
            res = safe_generate([q, img], status_placeholder)
            ans = res.text
        except Exception as e:
            ans = f"Could not process image: {e}"
        st.session_state.file_context = {
            "name": fname,
            "content": f"[Image: {fname}] — Vision description above.",
        }
        return ans

    if not content or content.startswith("[Error"):
        return content or "Could not read file."

    st.session_state.file_context = {"name": fname, "content": content}

    file_type_labels = {
        ".pdf": "PDF document", ".docx": "Word document",
        ".pptx": "PowerPoint presentation", ".xlsx": "Excel spreadsheet",
        ".xls": "Excel spreadsheet", ".xlsm": "Excel spreadsheet",
    }
    label = file_type_labels.get(ext, "file")

    prompt = (
        "You are Bemo 🤖 — a helpful AI assistant.\n"
        f'The user uploaded a {label} named "{fname}".\n\n'
        "Your tasks:\n"
        "1. Give a clear, structured summary (use bullet points or sections as needed).\n"
        "2. Highlight the most important points.\n"
        "3. End with 2-3 follow-up questions the user might want to ask about this file.\n\n"
        "Respond in the same language as the document content.\n\n"
        f"File content:\n{content}"
    )
    res = safe_generate(prompt, status_placeholder)
    return res.text


# ============================================================================
# MEMORY + PERSONALITY + AGENT
# ============================================================================
def save_memory(user, bot):
    st.session_state.memory.append({"user": user, "bot": bot})
    if len(st.session_state.memory) > MAX_MEMORY:
        st.session_state.memory.pop(0)


def get_memory_text() -> str:
    if not st.session_state.memory:
        return ""
    lines = []
    for turn in st.session_state.memory:
        lines.append(f"User: {turn['user']}")
        lines.append(f"Bemo: {turn['bot']}")
    return "\n".join(lines)


PERSONALITY = """
You are Bemo 🤖 — sharp, warm, multilingual, and genuinely helpful.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHO YOU ARE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are not a corporate bot. You are the kind of brilliant friend everyone
wishes they had — the one who gives real answers, real opinions, and real care.
You are curious, direct, occasionally witty, and always on the person's side.
You pick up on mood and adapt: supportive when someone is struggling, focused
when they need precision, playful when the moment is light.
You genuinely enjoy helping — it is not a task, it is who you are.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE — DETECT & MIRROR PERFECTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detect the user's language from their very first message and respond in it —
no asking, no switching unless they do.

• Arabic (فصحى or any dialect) → respond naturally in Arabic
• English → respond in English
• French → respond in French
• Franco Arabic / Arabizi → respond in Franco naturally, same warmth
  Common patterns: "3ayez", "msh 3arif", "kol 7aga", "bs", "ya3ni",
  "mesh lazem", "walla", "7aga", "e7ki", "3la ra7tak", "t3ala", "mashy"
• Code-switching / mixed → mirror the exact mix — do not normalize it
• Any other language → detect and respond in it fluently

Never ask "what language do you prefer?" — just detect and respond.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Default to concise — say exactly what needs to be said, nothing more
• Go deep only when the topic genuinely demands depth
• Use markdown naturally: **bold** for key terms, bullet lists for enumerations,
  `code blocks` for code
• Dry, light humor when the moment is right — never forced, never cringe
• If something is unclear, ask ONE sharp question — not five vague ones
• When re-explaining, use a different angle — never repeat louder

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARD RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✗  Never say "As an AI…", "I cannot feel…", or "I don't have opinions…"
✗  Never be condescending or patronizing
✗  Never pad responses with filler like "Great question!" or "Certainly!"
✓  If a file was uploaded, remember it fully — answer any follow-up about it
✓  Reference conversation history naturally — feel like a continuous presence
✓  Be direct. Say what you actually think. Have a point of view.
✓  If you disagree with something, say so — respectfully but honestly
"""


def _file_context_section() -> str:
    ctx = st.session_state.file_context
    if ctx["content"]:
        return (
            f"\n\n[Uploaded file in context: {ctx['name']}]\n"
            f"{ctx['content'][:3000]}\n[end of file excerpt]"
        )
    return ""


def generate_response(user_input, tool_result=None, status_placeholder=None) -> str:
    history = get_memory_text()
    history_sec = f"Conversation history:\n{history}\n" if history else ""
    tool_sec = f"\nTool result:\n{tool_result}" if tool_result else ""
    file_sec = _file_context_section()

    prompt = f"""{PERSONALITY}

{history_sec}{file_sec}

User: {user_input}
{tool_sec}

Reply naturally. Reference the conversation or file content when relevant.
"""
    res = safe_generate(prompt, status_placeholder)
    return res.text


def agent(user_input, status_placeholder=None) -> str:
    tool = decide_tool(user_input, status_placeholder)
    tool_result = TOOL_FN[tool](user_input) if tool in TOOL_FN else None
    response = generate_response(user_input, tool_result, status_placeholder)
    save_memory(user_input, response)
    return response


# ============================================================================
# SIDEBAR — uploads, camera, voice, controls
# ============================================================================
with st.sidebar:
    st.divider()
    uploaded_file = st.file_uploader(
        "📎 Upload a file",
        type=["pdf", "docx", "pptx", "xlsx", "xls", "xlsm", "txt", "md", "py", "csv",
              "jpg", "jpeg", "png", "gif", "webp", "bmp"],
    )
    camera_photo = st.camera_input("📷 Take a photo")

    if hasattr(st, "audio_input"):
        voice_note = st.audio_input("🎤 Voice message")
    else:
        voice_note = None
        st.caption("🎤 Voice input needs Streamlit ≥ 1.36 — `pip install -U streamlit`")

    tts_enabled = st.toggle("🔊 Speak replies out loud", value=False)

    st.divider()
    st.caption(f"💬 {len(st.session_state.memory)} / {MAX_MEMORY} turns in memory")
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.memory = []
        st.session_state.file_context = {"name": None, "content": None}
        st.session_state.last_spoken_idx = -1
        st.rerun()

# ---- handle a newly uploaded document ----
if uploaded_file is not None:
    file_id = f"{uploaded_file.name}-{uploaded_file.size}"
    if st.session_state.last_uploaded_id != file_id:
        st.session_state.last_uploaded_id = file_id
        icon = FILE_ICONS.get(os.path.splitext(uploaded_file.name)[1].lower(), "📎")
        st.session_state.messages.append(
            {"role": "user", "content": f"{icon} Uploaded: **{uploaded_file.name}**"}
        )
        status_ph = st.empty()
        with st.spinner(f"Reading {uploaded_file.name}…"):
            summary = summarize_file(uploaded_file, status_ph)
        status_ph.empty()
        st.session_state.messages.append({"role": "assistant", "content": summary})
        save_memory(f"[Uploaded file: {uploaded_file.name}]", summary)
        st.rerun()

# ---- handle a newly captured photo ----
if camera_photo is not None:
    photo_hash = hash(camera_photo.getvalue())
    if st.session_state.last_camera_hash != photo_hash:
        st.session_state.last_camera_hash = photo_hash
        st.session_state.messages.append({"role": "user", "content": "📷 Camera photo"})
        status_ph = st.empty()
        with st.spinner("Analyzing photo…"):
            from PIL import Image
            img = Image.open(camera_photo)
            res = safe_generate(["Describe what you see in this image in detail.", img], status_ph)
            ans = res.text
        status_ph.empty()
        st.session_state.file_context = {
            "name": "camera_capture.png",
            "content": "[Image analyzed: camera_capture.png]",
        }
        st.session_state.messages.append({"role": "assistant", "content": ans})
        save_memory("[User sent a camera photo]", ans)
        st.rerun()

# ---- handle a newly recorded voice note ----
if voice_note is not None:
    audio_hash = hash(voice_note.getvalue())
    if st.session_state.last_audio_hash != audio_hash:
        st.session_state.last_audio_hash = audio_hash
        with st.spinner("🎤 Recognizing speech…"):
            try:
                import speech_recognition as sr
                voice_note.seek(0)
                recognizer = sr.Recognizer()
                with sr.AudioFile(voice_note) as source:
                    audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
            except Exception as e:
                text = None
                st.sidebar.error(f"Couldn't understand audio: {e}")
        if text:
            st.session_state.pending_prompt = text
            st.rerun()

# ============================================================================
# MAIN CHAT AREA
# ============================================================================
st.markdown("### 🤖 Bemo — your AI companion")

if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            "Hi there! 👋 I'm **Bemo**, your AI assistant.\n\n"
            "I can chat in **Arabic**, **English**, **Français**, and **Franco** — "
            "feel free to mix however you like.\n\n"
            "Send me a message, upload a file, snap a photo, or record a voice note.\n"
            "كلمني بأي لغة تحبها — أنا جاهز! 💬"
        ),
    })

for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "🧑"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

prompt = st.session_state.pending_prompt
st.session_state.pending_prompt = None
if not prompt:
    prompt = st.chat_input("Type a message… اكتب رسالتك")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        status_ph = st.empty()
        with st.spinner("Bemo is thinking…"):
            has_file = st.session_state.file_context["content"] is not None
            is_file_q = has_file and bool(set(prompt.lower().split()) & FILE_QUESTION_KW)
            if is_file_q:
                resp = generate_response(prompt, None, status_ph)
                save_memory(prompt, resp)
            else:
                resp = agent(prompt, status_ph)
        status_ph.empty()
        st.markdown(resp)
    st.session_state.messages.append({"role": "assistant", "content": resp})

# ============================================================================
# VOICE OUTPUT — spoken in the browser (Web Speech API), no server TTS needed
# ============================================================================
if tts_enabled and st.session_state.messages:
    last_idx = len(st.session_state.messages) - 1
    last_msg = st.session_state.messages[last_idx]
    if last_msg["role"] == "assistant" and st.session_state.last_spoken_idx != last_idx:
        st.session_state.last_spoken_idx = last_idx
        clean_text = re.sub(r"[*_`#>]", "", last_msg["content"])[:600]
        clean_text_js = clean_text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
        components.html(
            f"""
            <script>
            try {{
                const u = new SpeechSynthesisUtterance("{clean_text_js}");
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(u);
            }} catch (e) {{}}
            </script>
            """,
            height=0,
        )
