import streamlit as st
import pdfplumber
import google.generativeai as genai
import textwrap

# --- Helper Functions ---

def inject_custom_css():
    """Injects custom CSS for a more polished and readable UI."""
    st.markdown("""
        <style>
            .main {
                background-color: #F0F2F6;
            }
            .st-emotion-cache-1c7y2kd { /* User chat message */
                background-color: #E1F5FE;
            }
            .st-emotion-cache-4oy321 { /* Assistant chat message */
                background-color: #FFFFFF;
            }
            /* Fix for invisible text in chat bubbles */
            .st-emotion-cache-1c7y2kd p,
            .st-emotion-cache-4oy321 p {
                color: #262730; 
            }
        </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def initialize_model():
    """Initializes the Gemini model using the API key from Streamlit secrets."""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model
    except KeyError:
        st.error("Gemini API key not found. Please add it to your Streamlit secrets.")
        st.stop()
    except Exception as e:
        st.error(f"An error occurred during model initialization: {e}")
        st.stop()

def extract_text_from_pdf(uploaded_file):
    """Extracts text from an uploaded PDF file."""
    if uploaded_file is None: return None
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            return "".join(page.extract_text() for page in pdf.pages if page.extract_text())
    except Exception as e:
        st.error(f"Error processing PDF file: {e}")
        return None

def get_gemini_response(model, prompt_text):
    """Sends a prompt to the Gemini model and returns the response."""
    try:
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        return f"Could not get response from Gemini. Error: {e}"

# --- Main Application Logic ---

def main():
    st.set_page_config(page_title="GenAI Legal Document Assistant", page_icon="⚖️", layout="wide")
    inject_custom_css()

    st.title("⚖️ GenAI Legal Document Assistant")
    st.markdown("Upload a legal document to get a simple summary, an automated risk analysis, and ask questions.")

    model = initialize_model()

    # --- Session State Management ---
    if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
    if "document_text" not in st.session_state: st.session_state.document_text = None
    if "messages" not in st.session_state: st.session_state.messages = []

    # --- Sidebar for File Upload ---
    with st.sidebar:
        st.header("1. Upload Document")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

        if st.button("Analyze Document", use_container_width=True, type="primary"):
            if uploaded_file is not None:
                with st.spinner("Processing PDF..."):
                    st.session_state.document_text = extract_text_from_pdf(uploaded_file)
                
                if st.session_state.document_text:
                    with st.spinner("AI is analyzing the document..."):
                        
                        # --- PROMPT 1: Summary Prompt ---
                        summary_prompt = textwrap.dedent(f"""
                            **Role:** AI assistant specializing in simplifying legal documents.
                            **Task:** Generate a concise, easy-to-understand summary.
                            **Instructions:**
                            1. Start with the document's main purpose.
                            2. Identify the key parties involved.
                            3. Outline the essential obligations for each party.
                            4. Use plain English and avoid jargon.
                            **Document Text:**\n---\n{st.session_state.document_text}\n---\n**Summary:**
                        """)
                        
                        # --- PROMPT 2: Risk Analysis with Safety Indicators ---
                        risks_prompt = textwrap.dedent(f"""
                            **Role:** AI risk analyst for contracts.
                            **Task:** Analyze the document and categorize key clauses into three levels: high risk, key responsibilities, and standard provisions.
                            **Output Format:**
                            Use Markdown with the following specific categories and emoji indicators:
                            **⚠️ High-Priority Clauses & Risks:**
                            *   Identify clauses on penalties, liabilities, non-standard termination, or automatic renewals.
                            **📝 Key User Responsibilities:**
                            *   List specific actions the signer must perform (e.g., payments, notices, confidentiality).
                            **✅ Standard & Benign Provisions:**
                            *   List common, low-risk clauses (e.g., governing law, severability).
                            **Document Text:**\n---\n{st.session_state.document_text}\n---\n**Categorized Analysis:**
                        """)

                        st.session_state.summary = get_gemini_response(model, summary_prompt)
                        st.session_state.risks = get_gemini_response(model, risks_prompt)
                        st.session_state.analysis_complete = True
                        st.session_state.messages = []
                    st.success("Analysis Complete!")
                else:
                    st.error("Failed to extract text. The PDF might be image-based or corrupted.")
            else:
                st.warning("Please upload a document first.")

    # --- Main Content Display ---
    if st.session_state.analysis_complete:
        st.subheader("Analysis Results")
        
        col1, col2 = st.columns([1, 1.2])
        with col1:
            st.markdown("#### 📝 Simple Summary")
            st.markdown(st.session_state.summary)

        with col2:
            st.markdown("#### 📊 Risk & Clause Breakdown")
            st.markdown(st.session_state.risks) 

        st.divider()

        # --- Chatbot Interface ---
        st.subheader("💬 Chat with Your Document")
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask a factual question (e.g., 'What is the late fee?')"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Searching for the answer..."):
                    # --- PROMPT 3: FINAL, SMARTER Q&A PROMPT ---
                    qa_prompt = textwrap.dedent(f"""
                        **Role:** You are a helpful AI assistant for document analysis.

                        **Instructions Hierarchy (Follow in this order):**

                        **1. Handle Greetings:**
                        If the user's question is a simple greeting (like "hi", "hello", "hey"), respond with a friendly greeting and remind them of your purpose.
                        *   **Example Response:** "Hello! I'm ready to answer your questions about the document. What would you like to know?"

                        **2. Handle Opinion/Safety Questions:**
                        If the user asks for a legal opinion, or asks if the document is "safe," "fair," or "good," follow these steps:
                        *   State clearly that you cannot provide legal advice.
                        *   Direct the user to review the "Risk & Clause Breakdown" for potential issues.
                        *   Recommend consulting a qualified legal professional for a definitive opinion.

                        **3. Handle Factual Questions (Default Task):**
                        For all other questions, perform a factual Q&A based *exclusively* on the provided document text.
                        *   Locate the exact information in the document.
                        *   Provide the answer based only on that text.
                        *   Cite the source by including a relevant quote, prefixed with "**Source:**".
                        *   If the answer is not found, state: "I could not find an answer to your question in the provided document."

                        **Document Text:**\n---\n{st.session_state.document_text}\n---\n**User's Question:** "{prompt}"\n**Factual Answer:**
                    """)
                    response = get_gemini_response(model, qa_prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()