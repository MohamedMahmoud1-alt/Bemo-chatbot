# Bemo: A Multimodal Conversational AI Assistant Powered by Google Gemini

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Features](#3-features)
4. [Technical Components](#4-technical-components)
   - 4.1 [Language Model Backend](#41-language-model-backend)
   - 4.2 [Tool System](#42-tool-system)
   - 4.3 [Tool Router](#43-tool-router)
   - 4.4 [Conversation Memory](#44-conversation-memory)
   - 4.5 [Voice Interface](#45-voice-interface)
   - 4.6 [Vision Interface](#46-vision-interface)
   - 4.7 [Graphical User Interface](#47-graphical-user-interface)
5. [Project Workflow](#5-project-workflow)
6. [Project Structure](#6-project-structure)
7. [Requirements](#7-requirements)
8. [Installation](#8-installation)
9. [Usage](#9-usage)
10. [Known Limitations](#10-known-limitations)
11. [Dependencies](#11-dependencies)

---

## 1. Project Overview

Bemo is a desktop-based conversational AI assistant built on top of Google's Gemini 2.5 Flash large language model. The system integrates a natural language processing backend with a set of specialized tools — including real-time web search, symbolic computation, live weather retrieval, document reading, and multimodal vision analysis — all exposed through a responsive Tkinter-based graphical user interface.

The project demonstrates the design and implementation of a tool-augmented language model agent capable of handling diverse user intents through a unified conversational interface. Bemo is intended to operate as a general-purpose assistant that detects and responds naturally in the user's own language — Arabic, English, French, Franco Arabic (Arabizi), or any mix of them — adapts to context through recent conversation memory, and provides voice-based input and output as an accessibility feature.

---

## 2. System Architecture

Bemo follows a modular agent architecture organized into the following layers:

```
User Input (Text / Voice / Image)
          |
          v
   Tool Router (Rule-based Pre-filter + Gemini Classification)
          |
     _____|_____________________________________
    |         |           |          |         |
 SEARCH   CALCULATE    WEATHER   DATETIME    NONE
 (DDGS)   (SymPy)     (wttr.in) (datetime) (direct LLM)
    |_________|___________|__________|_________|
                          |
              Prompt Construction
          (Personality + Memory + Tool Result)
                          |
                  Gemini 2.5 Flash
                          |
              Response + TTS Output
                          |
                  Tkinter GUI (Chat Bubble)
```

The agent layer ties together all subsystems: it receives the user message, dispatches it to the appropriate tool, injects the tool result and the recent conversation history into a structured prompt, and passes the prompt to Gemini for final response generation.

---

## 3. Features

| Feature                  | Implementation Detail                                                         |
|--------------------------|-------------------------------------------------------------------------------|
| Conversational AI        | Google Gemini 2.5 Flash via `google-generativeai`                             |
| Web Search               | Real-time DuckDuckGo search via the `ddgs` library (top 4 results)            |
| Symbolic Calculator      | Expression evaluation using SymPy; pop-up GUI calculator for manual input     |
| Weather Lookup           | Live weather data retrieved from `wttr.in` in compact format                  |
| Date and Time            | Local system date and time via Python `datetime`                              |
| Document Reading         | Reads PDF, Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`/`.xls`/`.xlsm`), and plain text/code files; up to 12,000 characters sent to Gemini for a structured summary |
| Image Analysis           | Uploaded images analyzed via Gemini Vision (`gemini-2.5-flash`)               |
| Live Camera Capture      | Webcam preview via OpenCV; captured frame passed to Gemini Vision             |
| Text-to-Speech (TTS)     | Offline speech synthesis via `pyttsx3` at 162 WPM; markdown-stripped output   |
| Speech-to-Text (STT)     | Microphone input recognized via Google Speech Recognition                     |
| Conversation Memory      | Last 15 turns stored in memory; passed with every prompt                      |
| Multilingual Support     | Detects and responds in the user's language — Arabic, English, French, Franco Arabic (Arabizi), or any mix — without asking |
| Rate Limit Handling      | Automatic retry with exponential back-off on HTTP 429 quota errors            |
| Dark-Themed GUI          | Catppuccin-inspired color palette; scrollable chat bubbles                    |

---

## 4. Technical Components

### 4.1 Language Model Backend

The system uses `google.generativeai.GenerativeModel` initialized with the `gemini-2.5-flash` model. All calls are wrapped in a `_ModelWrapper` class that implements automatic retry logic:

- Maximum retry attempts: 5
- Initial wait interval: 20 seconds
- Back-off strategy: exponential (doubles each retry, capped at 120 seconds)
- Retry condition: HTTP 429 response or quota-related error strings
- Live countdown displayed in the GUI status bar during retry intervals

> **Deprecation Notice:** The notebook produces a `FutureWarning` at runtime indicating that the `google.generativeai` package has been deprecated. It remains functional for the current implementation. Migration to the `google.genai` package is recommended for future development.

### 4.2 Tool System

Each tool is implemented as a standalone Python function:

**Web Search (`web_search`)**
Uses the `DDGS` class from the `ddgs` library to query DuckDuckGo and retrieve the body text of the top 4 results. Results are concatenated with newline separators and returned as a single string for injection into the Gemini prompt.

**Calculator (`calculator`)**
Strips any character that isn't a digit, operator, decimal point, parenthesis, `^`, `%`, or space from the query, then evaluates the remaining expression using `sympy.sympify`. Returns a string representation of the result, or an error message on failure. A separate interactive pop-up calculator widget built with Tkinter supports manual entry of arithmetic expressions (evaluated with Python's `eval`) via standard operator buttons (C, backspace, %, /, *, -, +, =).

**Weather (`get_weather`)**
Extracts the target city with a bilingual regex matching phrases such as "weather in X" or "طقس في X" — including Franco Arabic patterns like `ta2s`, `t2s`, `gaw`, `clima`, `7arara` — falling back to the last word of the query if no match is found. Constructs a URL of the form `https://wttr.in/{city}?format=3` and performs an HTTP GET request via the `requests` library. Returns the one-line weather summary string for the specified city.

**Date and Time (`get_datetime`)**
Uses `datetime.datetime.now()` and formats the result as a human-readable string including day name, full date, and 12-hour clock time.

**Document Reader (`read_file_content` / `summarize_file`)**
Dispatches by file extension to a dedicated extractor, each capped at 12,000 characters of extracted text:
- `.pdf` — page-by-page text extraction via `pypdf`
- `.docx` — paragraph text plus table cell contents via `python-docx`
- `.pptx` — text from every shape on every slide via `python-pptx`
- `.xlsx` / `.xls` / `.xlsm` — up to 80 rows per sheet via `openpyxl`
- any other extension (`.txt`, `.md`, `.py`, `.csv`, `.log`, etc.) — read directly as UTF-8 plain text

The extracted content is cached in `_last_file_context` so the user can ask natural follow-up questions about the file without re-uploading it. It is then sent to Gemini with instructions to produce a structured summary (bullet points/sections), highlight the most important points, suggest 2-3 follow-up questions, and reply in the same language as the document.

**Image Analyzer**
When an image is uploaded or captured, it is opened with PIL and passed — together with a user-provided question (default: "Describe what you see in this image in detail.") — directly to the `_raw_model` (`gemini-2.5-flash`) via `generate_content([question, image])`. The returned description is treated as Bemo's reply.

### 4.3 Tool Router

The routing system uses a two-stage decision process designed to minimize unnecessary API calls:

**Stage 1 — Rule-Based Pre-filter (`fast_decide`)**

Checks the user input against predefined keyword sets before making any API call:

- `WEATHER_KW`: `{"weather", "طقس", "جو", "حرارة", "درجة", "temperature", "forecast", "ta2s", "t2s", "gaw", "7arara", "clima"}`
- `DATETIME_KW`: `{"time", "date", "وقت", "تاريخ", "النهارده", "today", "اليوم", "الساعة", "now", "clock", "day", "month", "year", "sa3a", "yom", "ennaharda", "el-yom", "elsa3a"}`
- `CALC_KW`: `{"calc", "calculate", "حساب", "احسب", "يساوي", "equals", "compute", "e7seb", "7esab", "yesawi"}`
- Math detection: if more than 55% of characters in the input are numeric or arithmetic symbols (`0–9`, `+`, `-`, `*`, `/`, `(`, `)`, `.`, `^`, space), the router returns `CALCULATE`

**Stage 2 — Gemini Classification (`decide_tool`)**

If the rule-based filter returns no match, a minimal prompt is sent to Gemini requesting a single-word response from the set `{SEARCH, CALCULATE, WEATHER, DATETIME, NONE}`. The response is parsed and matched against the known labels. The system defaults to `NONE` (direct LLM response) if no label is identified.

### 4.4 Conversation Memory

Conversation history is stored as an in-session Python list of dictionaries, each containing `user` and `bot` keys, capped at the most recent 15 turns (`MAX_MEMORY = 15`) — the oldest turn is dropped once the cap is exceeded. The retained history is formatted as a plain-text dialogue transcript and injected into every response prompt, enabling Bemo to reference recent context naturally. Memory is cleared when the user clicks the "Clear" button in the GUI, at which point the memory list and the cached file context are both reset and the chat area is repopulated with Bemo's initial greeting.

### 4.5 Voice Interface

**Text-to-Speech (TTS)**

The `pyttsx3` engine is initialized at startup with a speech rate of 162 words per minute and full volume (1.0). Before synthesis, each response is stripped of markdown characters (`*`, `_`, `` ` ``, `#`, `>`) that would sound unnatural when spoken, and truncated to the first 600 characters. Speech runs in a background daemon thread protected by a `threading.Lock` to prevent concurrent synthesis requests from overlapping. TTS can be toggled on or off via the GUI header button.

**Speech-to-Text (STT)**

The `SpeechRecognition` library is used with the Google Speech Recognition backend. The recognizer's energy threshold is set to 300 with dynamic energy adjustment enabled, and ambient noise is calibrated for 0.8 seconds before listening begins. Recognition runs entirely in a background daemon thread with a listen timeout of 8 seconds and a maximum phrase duration of 15 seconds. Upon successful transcription, the resulting text is inserted into the input field so the user can review and optionally edit it before sending.

### 4.6 Vision Interface

**Image Upload**

The file dialog filters for common image extensions: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`, `.webp`. The selected image path is passed to the same Gemini Vision pipeline used for the camera in a background thread, and Bemo's response is displayed as a chat bubble labeled with a 🖼️ icon and the filename — no inline image preview is rendered in the chat area.

**Camera Capture**

OpenCV (`cv2.VideoCapture(0)`) opens the system's default webcam device. A live preview is rendered in a `Toplevel` dialog window, resized to 560 x 420 pixels and refreshed every 30 milliseconds using `win.after`. Pressing Space grabs a fresh frame via `cap.read()`, writes it to a temporary PNG file using `cv2.imwrite`, and passes it to the vision analysis pipeline. Pressing Escape cancels. The webcam is released and the preview window is closed immediately after capture or cancellation.

### 4.7 Graphical User Interface

The GUI is built entirely with Python's standard `tkinter` library. The color palette is inspired by the Catppuccin Mocha dark theme.

**Chat Area**

A scrollable `Canvas`-backed widget hosts chat bubbles built from padded `Frame` containers wrapping a `Text` widget, which handles native word-wrapping at the Segoe UI 11pt font. A lightweight regex-based renderer converts inline `**bold**`, `*italic*`, and `` `code` `` markdown into styled text tags, and bubble height is auto-sized from the wrapped line count. Bemo's (left) bubbles use `#2a2a3d` with a lavender left border; the user's (right) bubbles use `#353550` with a teal right border — both against the `#1e1e2e` chat background. The canvas auto-scrolls to the latest message after each update.

**Interactive Feedback**

Header buttons (Clear, Calculator, Sound toggle) and the send/upload/mic/camera icon buttons use a shared hover helper that swaps their background color on mouse enter/leave for clear visual feedback.

**Threading Model**

All operations that invoke the Gemini API, perform web requests, run speech recognition, or execute file I/O are dispatched to background `daemon` threads. UI updates from these threads are posted back to the main thread using `root.after(0, callback)` to comply with Tkinter's single-thread rendering constraint. Input controls are disabled during processing and re-enabled upon completion to prevent concurrent requests.

**Window Configuration**

- Default dimensions: 900 x 720 pixels (minimum 640 x 500, resizable)
- Main / chat background: `#1e1e2e`
- Header, input row, and status bar background: `#181825`

---

## 5. Project Workflow

```
User Input
    |
    +-- Text typed in input field, or
    +-- Voice recorded via microphone (STT transcription), or
    +-- Image uploaded from disk, or
    +-- Photo captured from webcam
    |
    v
Tool Router
    |
    +-- Stage 1: Rule-based keyword matching (zero API cost)
    +-- Stage 2: Gemini single-word classification (if Stage 1 yields no match)
    |
    v
Tool Execution (conditional)
    |
    +-- SEARCH   -> DuckDuckGo top-4 results
    +-- CALCULATE -> SymPy symbolic evaluation
    +-- WEATHER  -> wttr.in one-line summary
    +-- DATETIME -> System datetime string
    +-- (Image)  -> Gemini Vision analysis
    +-- (File)   -> Gemini document summarization
    +-- NONE     -> No tool; proceed directly
    |
    v
Prompt Construction
    |
    +-- System personality string prepended
    +-- Last 15 conversation turns appended
    +-- Tool result appended (if applicable)
    |
    v
Gemini 2.5 Flash Response Generation
    |
    v
Output Delivery
    |
    +-- Response rendered as chat bubble in GUI
    +-- TTS synthesis in background thread (if enabled)
    +-- Turn saved to conversation memory
```

---

## 6. Project Structure

Current structure (single-notebook implementation):

```
bemo-chatbot/
|
+-- Bemo_chatbot_v3.ipynb       # Complete system implementation
+-- README.md                   # Project documentation
```

Recommended structure for modular deployment:

```
bemo-chatbot/
|
+-- bemo/
|   +-- __init__.py
|   +-- agent.py                # Agent loop and tool dispatcher
|   +-- router.py               # Two-stage tool routing logic
|   +-- memory.py               # Session conversation memory
|   +-- voice.py                # TTS and STT modules
|   +-- gui.py                  # Tkinter interface and widgets
|   +-- tools/
|       +-- search.py           # DuckDuckGo web search
|       +-- calculator.py       # SymPy symbolic calculator
|       +-- weather.py          # wttr.in weather retrieval
|       +-- datetime_tool.py    # System date and time
|       +-- documents.py        # PDF / DOCX / PPTX / XLSX / text reader
|       +-- vision.py           # Gemini Vision image analysis
|       +-- camera.py           # OpenCV webcam capture
|
+-- requirements.txt
+-- README.md
```

---

## 7. Requirements

- Python 3.10 or later (developed and tested on Python 3.13.9, Windows)
- Jupyter Notebook or JupyterLab
- A valid Google AI Studio API key (available free at https://aistudio.google.com/app/apikey)
- An active internet connection (required for Gemini API, web search, weather, and Google STT)
- A working microphone (required for speech-to-text functionality)
- A webcam (required for live camera capture functionality)
- A desktop environment with display server support (Tkinter requires a graphical display)

---

## 8. Installation

Install all required packages by running the first cell of the notebook, or manually from the terminal:

```bash
pip install google-generativeai duckduckgo-search ddgs sympy pyttsx3 SpeechRecognition pyaudio opencv-python Pillow pypdf python-docx python-pptx openpyxl
```

**Windows — PyAudio installation:**

If `pip install pyaudio` fails due to missing build tools, use the pre-compiled wheel approach:

```bash
pip install pipwin
pipwin install pyaudio
```

**API Key Configuration:**

The notebook prompts for the API key at runtime using `getpass`. Alternatively, set the environment variable before launching Jupyter:

```bash
# Windows (Command Prompt)
set GOOGLE_API_KEY=your_key_here

# Windows (PowerShell)
$env:GOOGLE_API_KEY="your_key_here"

# Linux / macOS
export GOOGLE_API_KEY=your_key_here
```

---

## 9. Usage

1. Open `Bemo_chatbot_v3.ipynb` in Jupyter Notebook or JupyterLab.
2. Execute all cells sequentially from top to bottom. The recommended approach is **Kernel > Restart & Run All** to ensure a clean execution state.
3. Enter your Google AI Studio API key when prompted.
4. The Bemo chat window opens automatically after the final cell executes.

**Interface controls:**

| Control             | Function                                                          |
|---------------------|-------------------------------------------------------------------|
| Text field + Enter  | Send a typed message to Bemo                                      |
| Send button         | Send the typed message                                            |
| Microphone button   | Record speech; transcription is inserted into the input field     |
| File/image button   | Upload a document (PDF, Word, PowerPoint, Excel, text/code) for summarization or an image for visual analysis |
| Camera button       | Open webcam preview; capture a frame for visual analysis          |
| TTS toggle (header) | Enable or disable Bemo's spoken voice responses                   |
| Calculator (header) | Open the pop-up arithmetic calculator widget                      |
| Clear (header)      | Clear chat history and reset conversation memory                  |

**Interaction examples:**

- Typing `"What is the weather in Cairo?"` triggers the weather tool.
- Typing `"What is 2^10 + 5 * 3?"` triggers the calculator tool.
- Typing `"What time is it?"` triggers the datetime tool.
- Typing `"Who won the 2024 Nobel Prize in Physics?"` triggers the web search tool.
- Typing any general question triggers a direct Gemini response.
- Uploading a `.pdf`, `.docx`, `.pptx`, `.xlsx`, or `.py` file triggers document summarization.
- Uploading a `.jpg` image triggers Gemini Vision analysis.
- Asking a follow-up question about the last uploaded file reuses its cached content without re-reading it.

---

## 10. Known Limitations

- The `google.generativeai` SDK is officially deprecated. The system must be migrated to `google.genai` to receive continued support and bug fixes.
- Conversation memory is capped at the last 15 turns and is session-scoped only. No persistence mechanism exists between separate notebook executions.
- Speech-to-text relies on Google's online Speech Recognition service and requires an active internet connection; it is not available offline.
- The camera module uses device index `0` and does not support selection of alternative or external camera devices.
- Document summarization is truncated at the first 12,000 characters of extracted text. Content beyond this limit is silently discarded.
- The tool router does not implement intent disambiguation. Ambiguous queries default to `NONE` and are sent directly to Gemini without tool augmentation.
- Running the notebook on a headless server (without a display) will cause the Tkinter GUI cell to fail. A virtual display (e.g., `Xvfb` on Linux) would be required in such environments.

---

## 11. Dependencies

| Package                | Purpose                                           |
|------------------------|---------------------------------------------------|
| `google-generativeai`  | Gemini 2.5 Flash LLM and Vision API (deprecated)  |
| `ddgs`                 | DuckDuckGo web search interface                   |
| `duckduckgo-search`    | DuckDuckGo search backend (aliased by `ddgs`)     |
| `sympy`                | Symbolic mathematics and expression evaluation    |
| `pyttsx3`              | Offline text-to-speech synthesis                  |
| `SpeechRecognition`    | Microphone capture and speech-to-text             |
| `pyaudio`              | Audio I/O backend required by SpeechRecognition   |
| `opencv-python`        | Webcam access and frame processing                |
| `Pillow`               | Image loading and processing                      |
| `pypdf`                | PDF text extraction                               |
| `python-docx`          | Word (`.docx`) paragraph and table text extraction |
| `python-pptx`          | PowerPoint (`.pptx`) slide text extraction        |
| `openpyxl`             | Excel (`.xlsx`/`.xls`/`.xlsm`) row data extraction |
| `requests`             | HTTP requests for the weather API                 |
| `tkinter`              | Graphical user interface (Python standard library)|
| `threading`            | Non-blocking background task execution            |
| `datetime`             | Local date and time retrieval                     |
| `sympy`                | Symbolic computation for the calculator tool      |
| `warnings`             | Suppression of known deprecation warnings         |

---

*Developed and tested on Python 3.13.9, Windows 10/11.*
*Primary language model: Google Gemini 2.5 Flash (`gemini-2.5-flash`).*

## Project Team

- **Ahmed Mohamed Ghareeb Taha**
- **Mohamed Mahmoud Mohamed Salem**
- **Majid Basem Mohamed Abdrabo**
- **Mazen Elsayed Hmam Hussein**
