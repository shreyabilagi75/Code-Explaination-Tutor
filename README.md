# Code Explanation Tutor

A simple Streamlit app that helps beginner/intermediate programming students
understand source code by letting them upload a file, ask a question, and
get a structured, beginner-friendly explanation.

## Workflow

Select Language → Upload Code → Ask Doubt → Analyze Code → Explain →
Give Example → Give Practice Question

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set your Anthropic API key as an environment variable:

   ```bash
   # macOS / Linux
   export ANTHROPIC_API_KEY="your-api-key-here"

   # Windows (PowerShell)
   $env:ANTHROPIC_API_KEY="your-api-key-here"
   ```

3. Run the app:

   ```bash
   streamlit run app.py
   ```

4. Open the local URL Streamlit prints in your terminal (usually
   `http://localhost:8501`).

## How to use it

1. **Select the programming language** of your code (Python, C, C++, Java,
   JavaScript, SQL, or Other).
2. **Upload your source code file** (`.py`, `.c`, `.cpp`, `.java`, `.js`,
   `.sql`, `.txt`, and several other common formats are supported).
3. **Type your question or doubt**, for example:
   - "What does this function do?"
   - "Where does execution start?"
   - "How does data flow through this program?"
   - "Why am I getting this error?"
4. Click **Explain Code**.
5. Review the results:
   - **Code Preview** — the uploaded code, so you can follow along.
   - **Explanation** — a direct answer, the relevant code snippet, a
     beginner-friendly explanation, and a small example. For
     execution/data-flow questions you'll also see a simple
     Input → Variables → Functions → Processing → Output walkthrough. For
     error questions you'll see Error → Cause → Relevant Code → Fix → Why
     the Fix Works.
   - **Practice Question** — a short question to check your understanding,
     with the hint/answer hidden behind an expander so you can try first.

## Notes for students / instructors

- The app keeps things intentionally simple: one file, one question, one
  explanation at a time — ask again for follow-up questions.
- Large files are truncated to the first ~20,000 characters to keep
  explanations focused and fast.
- If no file or no question is provided, the app will show a clear
  validation message instead of failing silently.
- The code in `app.py` is organized into small, commented functions
  (`read_file_content`, `build_system_prompt`, `call_claude`,
  `split_sections`, etc.) so it's easy to read and extend.
