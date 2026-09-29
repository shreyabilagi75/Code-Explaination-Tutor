"""
Code Explanation Tutor
-----------------------
A simple Streamlit app that helps beginner/intermediate programming
students understand source code by asking questions about it.

Workflow:
    Select Language -> Upload Code -> Ask Doubt -> Analyze Code
    -> Explain -> Give Example -> Give Practice Question

Run with:
    streamlit run app.py

Requires the environment variable ANTHROPIC_API_KEY to be set.
"""

import os
import re

import streamlit as st
from anthropic import Anthropic


# ---------------------------------------------------------------------------
# Configuration / Constants
# ---------------------------------------------------------------------------

LANGUAGES = ["Python", "C", "C++", "Java", "JavaScript", "SQL", "Other"]

# Map dropdown language -> language tag used for syntax highlighting in
# st.code(). "Other" has no fixed tag, so we fall back to plain text.
CODE_HIGHLIGHT_MAP = {
    "Python": "python",
    "C": "c",
    "C++": "cpp",
    "Java": "java",
    "JavaScript": "javascript",
    "SQL": "sql",
    "Other": "text",
}

# File extensions we accept in the uploader. Kept broad so most common
# source files (and plain text) can be uploaded.
ACCEPTED_EXTENSIONS = [
    "py", "c", "cc", "cpp", "cxx", "h", "hpp",
    "java", "js", "jsx", "ts", "tsx",
    "sql", "txt", "cs", "rb", "go", "php", "kt", "swift", "m",
]

MAX_CHARS = 20000  # Cap the amount of code we send to the model.
MODEL_NAME = "claude-sonnet-4-6"

# Keywords used to decide which extra structure to ask the model for.
FLOW_KEYWORDS = [
    "execution", "start", "flow", "data flow", "how does data",
    "order", "call", "run", "trace",
]
ERROR_KEYWORDS = ["error", "bug", "exception", "traceback", "crash", "fail"]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def read_file_content(uploaded_file):
    """Read an uploaded file and return (content, error_message).

    Tries UTF-8 first, then falls back to latin-1 so most text-based
    source files can be read without crashing the app.
    """
    if uploaded_file is None:
        return None, "No file uploaded."

    raw_bytes = uploaded_file.getvalue()

    if len(raw_bytes) == 0:
        return None, "The uploaded file is empty."

    content = None
    for encoding in ("utf-8", "latin-1"):
        try:
            content = raw_bytes.decode(encoding)
            break
        except (UnicodeDecodeError, AttributeError):
            continue

    if content is None:
        return None, (
            "Could not read this file as text. Please upload a plain "
            "source-code or text file."
        )

    truncated_note = ""
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS]
        truncated_note = (
            "\n\n[Note: the file was long, so only the first "
            f"{MAX_CHARS} characters were used for the explanation.]"
        )

    return content, truncated_note if truncated_note else None


def detect_question_type(question: str) -> str:
    """Classify the question so the prompt can ask for the right structure.

    Returns one of: "error", "flow", "general"
    """
    q = question.lower()
    if any(word in q for word in ERROR_KEYWORDS):
        return "error"
    if any(word in q for word in FLOW_KEYWORDS):
        return "flow"
    return "general"


def build_system_prompt() -> str:
    """The fixed instructions that tell Claude how to teach, not just answer."""
    return (
        "You are a patient, encouraging programming tutor for beginner and "
        "intermediate students. You will be given a piece of source code, "
        "its programming language, and a student's question about it. "
        "Explain things simply, avoid unnecessary jargon, and always ground "
        "your explanation in the actual code provided.\n\n"
        "Format your ENTIRE reply using Markdown with EXACTLY these section "
        "headers, in this order, using '## ' before each title. Only include "
        "a section if it is relevant to the question, but ALWAYS include "
        "'## Practice Question' and '## Hint / Answer' at the end:\n\n"
        "## Direct Answer\n"
        "## Relevant Code Reference\n"
        "## Execution Flow\n"
        "## Error, Cause and Fix\n"
        "## Beginner-Friendly Explanation\n"
        "## Small Example\n"
        "## Practice Question\n"
        "## Hint / Answer\n\n"
        "Rules:\n"
        "- '## Relevant Code Reference' should quote only the small, "
        "specific snippet(s) of the student's code that matter, using a "
        "fenced code block.\n"
        "- '## Execution Flow' should only appear for questions about where "
        "the program starts or how data moves. Describe it as a simple "
        "chain like: Input -> Variables -> Functions -> Processing -> "
        "Output, adapted to the actual code.\n"
        "- '## Error, Cause and Fix' should only appear for error/debugging "
        "questions, and inside it walk through: Error, Cause, Relevant "
        "Code, Fix, Why the Fix Works, in that order.\n"
        "- '## Small Example' should be a short, separate, minimal example "
        "illustrating the underlying concept (not just a repeat of the "
        "student's code).\n"
        "- '## Practice Question' should be one small question that checks "
        "understanding of the concept just explained.\n"
        "- '## Hint / Answer' should give a short hint first, then the "
        "answer, clearly separated.\n"
        "- Keep the whole reply focused and readable for a beginner; do not "
        "pad it with unnecessary length."
    )


def build_user_prompt(language: str, code: str, question: str, q_type: str) -> str:
    """Assemble the actual message sent to the model for this request."""
    hint_line = {
        "error": "This looks like an error/debugging question.",
        "flow": "This looks like a question about execution order or data flow.",
        "general": "This is a general understanding question.",
    }[q_type]

    return (
        f"Programming language: {language}\n"
        f"Question type hint: {hint_line}\n\n"
        f"Student's question:\n{question}\n\n"
        f"Source code:\n```{language.lower()}\n{code}\n```"
    )


def call_claude(system_prompt: str, user_prompt: str):
    """Call the Anthropic API and return (response_text, error_message)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, (
            "ANTHROPIC_API_KEY environment variable is not set. Please set "
            "it before running the app (see README.md)."
        )

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_parts = [b.text for b in response.content if getattr(b, "type", "") == "text"]
        full_text = "\n".join(text_parts).strip()
        if not full_text:
            return None, "The model returned an empty response. Please try again."
        return full_text, None
    except Exception as exc:  # noqa: BLE001 - surface any API/network issue to the user
        return None, f"Something went wrong while contacting the AI service: {exc}"


def split_sections(response_text: str):
    """Split the model's Markdown reply into (main_text, practice_text).

    main_text = everything before "## Practice Question"
    practice_text = "## Practice Question" section + "## Hint / Answer" section
    """
    marker = "## Practice Question"
    idx = response_text.find(marker)
    if idx == -1:
        return response_text.strip(), None
    main_text = response_text[:idx].strip()
    practice_text = response_text[idx:].strip()
    return main_text, practice_text


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Code Explanation Tutor", page_icon="🧑‍🏫", layout="wide")

st.title("🧑‍🏫 Code Explanation Tutor")
st.caption(
    "Upload your code, ask a question about it, and get a beginner-friendly "
    "explanation with an example and a practice question."
)

st.divider()

# --- Step 1: Language selection -------------------------------------------
st.subheader("1. Select the programming language")
language = st.selectbox("Language", LANGUAGES, index=0)

custom_language = None
if language == "Other":
    custom_language = st.text_input(
        "Please specify the language",
        placeholder="e.g. Kotlin, Rust, PHP...",
    )

effective_language = custom_language.strip() if (language == "Other" and custom_language) else language

# --- Step 2: File upload ----------------------------------------------------
st.subheader("2. Upload your source code file")
uploaded_file = st.file_uploader(
    "Upload a source code / project file",
    type=ACCEPTED_EXTENSIONS,
    accept_multiple_files=False,
    help="Supported: .py, .c, .cpp, .java, .js, .ts, .sql, .txt and other common source formats.",
)

# --- Step 3: Question input -------------------------------------------------
st.subheader("3. Ask your doubt about the code")
question = st.text_area(
    "Your question",
    placeholder=(
        "Examples:\n"
        "- What does this function do?\n"
        "- Where does execution start?\n"
        "- How does data flow through this program?\n"
        "- Explain this code.\n"
        "- Why is this loop used?\n"
        "- What will be the output?\n"
        "- Why am I getting this error?"
    ),
    height=120,
)

# --- Step 4: Action button --------------------------------------------------
st.subheader("4. Get your explanation")
explain_clicked = st.button("🔍 Explain Code", type="primary")

st.divider()

# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

if explain_clicked:
    # ---- Input validation ----
    validation_errors = []

    if uploaded_file is None:
        validation_errors.append("Please upload a source code file before requesting an explanation.")

    if not question or not question.strip():
        validation_errors.append("Please enter your question or doubt about the code.")

    if language == "Other" and not (custom_language and custom_language.strip()):
        validation_errors.append("Please specify the language name since you selected 'Other'.")

    if validation_errors:
        for msg in validation_errors:
            st.error(msg)
    else:
        code_content, read_note_or_error = read_file_content(uploaded_file)

        if code_content is None:
            # read_file_content returns an error message in this case
            st.error(read_note_or_error)
        else:
            if read_note_or_error:
                st.info(read_note_or_error)

            # Store in session state so the preview persists across reruns
            st.session_state["last_code"] = code_content
            st.session_state["last_language"] = effective_language
            st.session_state["last_filename"] = uploaded_file.name

            q_type = detect_question_type(question)
            system_prompt = build_system_prompt()
            user_prompt = build_user_prompt(effective_language, code_content, question.strip(), q_type)

            with st.spinner("Analyzing your code and preparing an explanation..."):
                response_text, api_error = call_claude(system_prompt, user_prompt)

            if api_error:
                st.error(api_error)
            else:
                main_text, practice_text = split_sections(response_text)
                st.session_state["last_main_text"] = main_text
                st.session_state["last_practice_text"] = practice_text
                st.success("Explanation generated below.")

# ---------------------------------------------------------------------------
# Code preview section
# ---------------------------------------------------------------------------

if "last_code" in st.session_state:
    with st.expander(f"📄 Code Preview — {st.session_state.get('last_filename', '')}", expanded=False):
        highlight_lang = CODE_HIGHLIGHT_MAP.get(language, "text")
        st.code(st.session_state["last_code"], language=highlight_lang)

# ---------------------------------------------------------------------------
# Explanation / Result section
# ---------------------------------------------------------------------------

if "last_main_text" in st.session_state:
    st.subheader("📘 Explanation")
    st.markdown(st.session_state["last_main_text"])

# ---------------------------------------------------------------------------
# Practice question section
# ---------------------------------------------------------------------------

if "last_practice_text" in st.session_state and st.session_state["last_practice_text"]:
    st.subheader("✏️ Practice Question")
    practice_text = st.session_state["last_practice_text"]

    # Try to separate "Practice Question" from "Hint / Answer" for a nicer
    # UI (hint hidden behind an expander so students can try first).
    hint_marker = "## Hint / Answer"
    hint_idx = practice_text.find(hint_marker)

    if hint_idx != -1:
        question_part = practice_text[:hint_idx].replace("## Practice Question", "").strip()
        hint_part = practice_text[hint_idx:].replace("## Hint / Answer", "").strip()

        st.markdown(question_part)
        with st.expander("💡 Show Hint / Answer"):
            st.markdown(hint_part)
    else:
        st.markdown(practice_text.replace("## Practice Question", "").strip())

elif not explain_clicked and "last_main_text" not in st.session_state:
    st.caption("Your explanation and practice question will appear here after you click **Explain Code**.")
