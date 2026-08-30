# 🤖 Bemo Chatbot

**Bemo** is a sharp, multilingual AI companion built to feel genuinely human. She converses naturally in **Arabic, English, French, Franco (Arabizi), and any mix**, searches the web, solves math, checks the weather, and reads **PDFs, PowerPoints, Word docs, Excel sheets, and images**.

| | |
|---|---|
| **Model** | Gemini 2.5 Flash |
| **Interface** | Tkinter desktop GUI (Catppuccin Mocha theme) |
| **Languages** | Arabic, English, French, Franco Arabic |

## Features

- 🌍 **Multilingual conversation** — understands and replies in Arabic, English, French, or Franco Arabic, including mixed input
- 🔎 **Web search** — pulls live results via DuckDuckGo for up-to-date answers
- 🧮 **Calculator** — solves math expressions using SymPy
- 🌦️ **Weather & date/time** — bilingual keyword detection (including Franco Arabic slang) for quick lookups
- 📎 **File understanding** — reads and answers questions about PDFs, Word docs, PowerPoint slides, Excel sheets, and images
- 🗣️ **Voice** — text-to-speech replies and speech-to-text input
- 📷 **Camera capture** — snap a photo directly from the webcam to ask about it
- 🧠 **Conversation memory** — keeps the last 15 turns of context for coherent follow-ups
- 🔁 **Auto-retry** — handles Gemini API rate limits (429s) gracefully with backoff

## Tech Stack

- `google-generativeai` — Gemini 2.5 Flash
- `ddgs` (DuckDuckGo Search) — web search
- `sympy` — calculator
- `pyttsx3`, `SpeechRecognition`, `pyaudio` — voice I/O
- `opencv-python`, `Pillow` — camera capture & image handling
- `pypdf`, `python-docx`, `python-pptx`, `openpyxl` — document reading
- `tkinter` — GUI

## Setup

1. Clone the repo and open `Bemo_chatbot_v3.ipynb`
2. Install dependencies:
   ```bash
   pip install google-generativeai ddgs sympy pyttsx3 SpeechRecognition pyaudio opencv-python Pillow pypdf python-docx python-pptx openpyxl
   ```
3. Run the notebook — you'll be prompted to enter your `GOOGLE_API_KEY` (or set it as an environment variable beforehand)
4. Run all cells to launch the Tkinter GUI

## Team

- Mohamed Mahmoud Mohamed Salem
- Ahmed Mohamed Ghareeb Taha
- Majid Basem Mohamed Abdrabo
- Mazen Elsayed Hmam Hussein
