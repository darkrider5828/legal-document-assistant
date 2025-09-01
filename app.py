import streamlit as st
import pdfplumber
import google.generativeai as genai
import textwrap
import markdown2
from weasyprint import HTML, CSS

# --- Page Configuration ---
st.set_page_config(
    page_title="Legal Eagle AI",
    page_icon="🦅",
    layout="wide"
)

# --- Helper Functions ---

def inject_custom_css():
    """Injects custom CSS for a professional UI."""
    st.markdown("""
        <style>
            .main { background-color: #F0F2F6; }
            .st-emotion-cache-1c7y2kd { background-color: #E1F5FE; } /* User chat message */
            .st-emotion-cache-4oy321 { background-color: #FFFFFF; } /* Assistant chat message */
            .st-emotion-cache-1c7y2kd p, .st-emotion-cache-4oy321 p { color: #262730; } /* Chat text color */
            .st-emotion-cache-1v0mbdj > button:first-child { font-weight: 600; } /* Style primary button */
        </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def initialize_model():
    """Initializes the Gemini model from Streamlit secrets."""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error initializing AI model. Please check your API key. Details: {e}")
        st.stop()

def extract_text_from_pdf(uploaded_file):
    """Extracts text from an uploaded PDF file."""
    if not uploaded_file: return None
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            return "".join(page.extract_text() for page in pdf.pages if page.extract_text())
    except Exception:
        st.error("Error processing PDF file. It might be corrupted or image-based.")
        return None

def get_gemini_response(model, prompt_text):
    """Sends a prompt to the Gemini model."""
    try:
        return model.generate_content(prompt_text).text
    except Exception as e:
        return f"Could not get response from AI. Error: {e}"

# --- NEW FUNCTION FOR PDF GENERATION ---
def create_pdf_report(markdown_content):
    """Converts a markdown string into a styled PDF bytes object."""
    html_content = markdown2.markdown(markdown_content, extras=["fenced-code-blocks", "tables"])
    
    # Professional CSS for styling the PDF report
    css_style = CSS(string="""
        @page { size: A4; margin: 2cm; }
        body { font-family: 'Helvetica', sans-serif; font-size: 11pt; line-height: 1.6; }
        h1, h2, h3 { font-family: 'Arial', sans-serif; color: #1a1a1a; }
        h1 { font-size: 24pt; border-bottom: 3px solid #007BFF; padding-bottom: 10px; margin-bottom: 20px; }
        h2 { font-size: 16pt; color: #007BFF; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        ul { list-style-type: disc; padding-left: 20px; }
        li { margin-bottom: 10px; }
        p { text-align: justify; }
        code { background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: monospace; }
    """)
    
    pdf_bytes = HTML(string=html_content).write_pdf(stylesheets=[css_style])
    return pdf_bytes

# --- Main Application Logic ---

def main():
    inject_custom_css()
    st.title("🦅 Legal Eagle AI: Your Personal Contract Co-Pilot")

    model = initialize_model()

    # Initialize session state
    if "analysis_done" not in st.session_state: st.session_state.analysis_done = False
    if "messages" not in st.session_state: st.session_state.messages = []
    if "doc_text" not in st.session_state: st.session_state.doc_text = None

    # --- Sidebar for File Upload ---
    with st.sidebar:
        st.header("Upload Your Document")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        
        if st.button("Analyze Document", use_container_width=True, type="primary"):
            if uploaded_file:
                with st.spinner("Processing PDF..."):
                    st.session_state.doc_text = extract_text_from_pdf(uploaded_file)
                
                if st.session_state.doc_text:
                    with st.spinner("The Eagle is analyzing... This may take a moment."):
                        # ... [All your AI prompts remain the same here] ...
                        summary_prompt = textwrap.dedent(f"Summarize this document's purpose, parties, and key obligations in plain English:\n---\n{st.session_state.doc_text}")
                        risks_prompt = textwrap.dedent(f"""Analyze this document... (Your full risk prompt)""")
                        dashboard_prompt = textwrap.dedent(f"""From this document, extract key entities... (Your full dashboard prompt)""")
                        
                        st.session_state.summary = get_gemini_response(model, summary_prompt)
                        st.session_state.risks = get_gemini_response(model, risks_prompt)
                        st.session_state.dashboard = get_gemini_response(model, dashboard_prompt)
                        
                        st.session_state.analysis_done = True
                        st.session_state.messages = []
                    st.success("Analysis Complete!")
            else:
                st.warning("Please upload a document first.")

    # --- Main Content Display ---
    if st.session_state.analysis_done:
        # ... [The display logic for dashboard, summary, and risks remains the same] ...
        st.subheader("Executive Overview")
        st.markdown(st.session_state.dashboard)
        st.divider()

        st.subheader("Detailed Analysis")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📝 Simple Summary")
            st.markdown(st.session_state.summary)
        with col2:
            st.markdown("#### 📊 Risk & Clause Breakdown")
            st.markdown(st.session_state.risks)
        
        # --- UPDATED Download Report Button ---
        full_report_md = f"""
# Legal Eagle AI Analysis Report

{st.session_state.dashboard}
---
## Simple Summary
{st.session_state.summary}
---
## Risk & Clause Breakdown
{st.session_state.risks}
        """
        
        # Generate PDF bytes using the new function
        pdf_bytes = create_pdf_report(full_report_md)
        
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_bytes,
            file_name="Legal_Eagle_AI_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        st.divider()

        # --- Chatbot Interface ---
        st.subheader("💬 Chat with Your Document")
        # ... [The chatbot logic remains the same] ...
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

        if prompt := st.chat_input("Ask a factual question (e.g., 'What is the late fee?')"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            
            with st.spinner("Thinking..."):
                qa_prompt = textwrap.dedent(f"""... (Your full, smart Q&A prompt)...""")
                response = get_gemini_response(model, qa_prompt)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.chat_message("assistant").write(response)

if __name__ == "__main__":
    main()