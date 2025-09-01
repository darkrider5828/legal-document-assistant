import streamlit as st
import pdfplumber
import google.generativeai as genai
import textwrap

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
    except KeyError:
        st.error("Gemini API key not found. Please add it to your Streamlit secrets (`.streamlit/secrets.toml`).")
        st.stop()
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

# --- Main Application Logic ---

def main():
    inject_custom_css()
    st.title("🦅 Legal Eagle AI: Your Personal Contract Co-Pilot")

    model = initialize_model()

    # Initialize session state
    if "analysis_done" not in st.session_state: st.session_state.analysis_done = False
    if "messages" not in st.session_state: st.session_state.messages = []
    if "doc_text" not in st.session_state: st.session_state.doc_text = None
    if "summary" not in st.session_state: st.session_state.summary = ""
    if "risks" not in st.session_state: st.session_state.risks = ""
    if "dashboard" not in st.session_state: st.session_state.dashboard = ""


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
                        # --- Multi-Prompt AI Analysis ---
                        
                        # Prompt 1: Summary
                        summary_prompt = textwrap.dedent(f"Summarize this document's purpose, parties, and key obligations in plain English:\n---\n{st.session_state.doc_text}")
                        
                        # Prompt 2: Risk Analysis with Indicators
                        risks_prompt = textwrap.dedent(f"""
                            Analyze this document for risks and key clauses. Categorize them using these exact markdown headers and emojis:
                            - **⚠️ High-Priority Risks:** (e.g., penalties, liabilities, auto-renewals)
                            - **📝 Key Responsibilities:** (e.g., payment duties, notice periods, confidentiality)
                            - **✅ Standard Provisions:** (e.g., governing law, severability)
                            Document:\n---\n{st.session_state.doc_text}
                        """)

                        # Prompt 3: Executive Dashboard & Action Items (THE "WOW" FACTOR)
                        dashboard_prompt = textwrap.dedent(f"""
                            From this document, extract key entities and generate a user checklist. Use these exact markdown headers:
                            - **📊 Key Information Dashboard:** (List Parties, Key Dates, Financial Amounts)
                            - **📋 Recommended Action Items:** (Create a checklist of next steps for the user)
                            Document:\n---\n{st.session_state.doc_text}
                        """)

                        st.session_state.summary = get_gemini_response(model, summary_prompt)
                        st.session_state.risks = get_gemini_response(model, risks_prompt)
                        st.session_state.dashboard = get_gemini_response(model, dashboard_prompt)
                        
                        st.session_state.analysis_done = True
                        st.session_state.messages = []
                    st.success("Analysis Complete!")
            else:
                st.warning("Please upload a document first.")

    # --- Main Content Display ---
    if not st.session_state.analysis_done:
        st.info("Upload your document and click 'Analyze Document' to begin.")
    else:
        # --- The Executive Dashboard ---
        st.subheader("Executive Overview")
        st.markdown(st.session_state.dashboard)
        st.divider()

        # --- Detailed Analysis Columns ---
        st.subheader("Detailed Analysis")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📝 Simple Summary")
            st.markdown(st.session_state.summary)
        with col2:
            st.markdown("#### 📊 Risk & Clause Breakdown")
            st.markdown(st.session_state.risks)
        
        # --- Download Report Button ---
        full_report = f"""
# Legal Eagle AI Analysis Report

## Executive Overview
{st.session_state.dashboard}
---
## Simple Summary
{st.session_state.summary}
---
## Risk & Clause Breakdown
{st.session_state.risks}
        """
        st.download_button(
            label="📥 Download Full Report",
            data=full_report,
            file_name="Legal_Eagle_AI_Report.md",
            mime="text/markdown",
            use_container_width=True
        )

        st.divider()

        # --- Chatbot Interface ---
        st.subheader("💬 Chat with Your Document")
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

        if prompt := st.chat_input("Ask a factual question (e.g., 'What is the late fee?')"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            
            with st.spinner("Thinking..."):
                # The final, smartest Q&A prompt
                qa_prompt = textwrap.dedent(f"""
                    **Role:** AI Assistant answering questions about a legal document.
                    **Instructions Hierarchy:**
                    1. **Handle Greetings:** If the user says "hi" or "hello", give a friendly greeting.
                    2. **Handle Opinions:** If the user asks if the doc is "safe" or "fair", state you cannot give legal advice and direct them to the risk analysis.
                    3. **Handle Factual Questions:** Answer questions using *only* the document text provided. Cite your source with a quote. If the answer isn't in the text, say so.
                    **Document Text:**\n---\n{st.session_state.doc_text}\n---\n**User's Question:** "{prompt}"\n**Answer:**
                """)
                response = get_gemini_response(model, qa_prompt)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.chat_message("assistant").write(response)

if __name__ == "__main__":
    main()