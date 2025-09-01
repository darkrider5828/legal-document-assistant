import streamlit as st
import pdfplumber
import google.generativeai as genai
import textwrap

# --- Helper Functions ---

def inject_custom_css():
    """
    Injects custom CSS for a more polished and readable UI.
    This version includes the fix for invisible chat text.
    """
    st.markdown("""
        <style>
            .main {
                background-color: #F0F2F6;
            }
            
            /* User chat message */
            .st-emotion-cache-1c7y2kd { 
                background-color: #E1F5FE; /* A light blue for user messages */
            }

            /* Assistant chat message */
            .st-emotion-cache-4oy321 { 
                background-color: #FFFFFF;
            }

            /* --- FIX FOR INVISIBLE TEXT --- */
            /* Ensure text inside chat messages is dark and readable */
            .st-emotion-cache-1c7y2kd p,
            .st-emotion-cache-4oy321 p {
                color: #262730; /* A dark color for the text, ensures visibility */
            }
            /* --- END OF FIX --- */
            
            .stButton>button {
                border-radius: 5px;
            }
        </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def initialize_model():
    """
    Initializes the Gemini model using the API key from Streamlit secrets.
    Uses st.cache_resource to ensure the model is loaded only once.
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        # Using the gemini-1.5-flash model as specified in your code
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model
    except KeyError:
        st.error("Gemini API key not found. Please add it to `.streamlit/secrets.toml`.")
        st.stop()
    except Exception as e:
        st.error(f"An error occurred during model initialization: {e}")
        st.stop()

def extract_text_from_pdf(uploaded_file):
    """Extracts text from an uploaded PDF file."""
    if uploaded_file is None:
        return None
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
    # --- Page Configuration ---
    st.set_page_config(
        page_title="GenAI Legal Document Assistant",
        page_icon="⚖️",
        layout="wide"
    )
    inject_custom_css()

    st.title("⚖️ GenAI Legal Document Assistant")
    st.markdown("Understand your legal documents instantly. Upload a PDF to get a simple summary, risk analysis, and ask questions.")

    model = initialize_model()

    # --- Session State Management ---
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    if "document_text" not in st.session_state:
        st.session_state.document_text = None
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- Sidebar for File Upload ---
    with st.sidebar:
        st.header("1. Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            help="Only PDF files are accepted."
        )

        if st.button("Analyze Document", use_container_width=True, type="primary"):
            if uploaded_file is not None:
                with st.spinner("Processing PDF..."):
                    st.session_state.document_text = extract_text_from_pdf(uploaded_file)
                
                if st.session_state.document_text:
                    with st.spinner("AI is analyzing the document. This may take a moment..."):
                        
                        # --- PROMPT 1: The Summary Prompt (Unchanged) ---
                        summary_prompt = textwrap.dedent(f"""
                            **Role:** You are an AI assistant specializing in simplifying complex legal documents for a general audience. Your goal is to provide clarity, not legal advice.
                            **Task:** Analyze the following legal document and generate a concise, easy-to-understand summary.
                            **Instructions:**
                            1.  **Core Purpose:** Begin with a single sentence that clearly states the document's main purpose.
                            2.  **Key Parties:** Identify the primary parties involved and their roles.
                            3.  **Main Obligations:** In a short paragraph, outline the essential obligations of each party.
                            4.  **Language:** Use simple, plain English. Avoid jargon.
                            **Document Text:**\n---\n{st.session_state.document_text}\n---\n**Generated Summary:**
                        """)
                        
                        # --- PROMPT 2: EDITED Risk Analysis with Safety Indicators ---
                        risks_prompt = textwrap.dedent(f"""
                            **Role:** AI risk analyst for contracts.
                            **Task:** Analyze the document and categorize key clauses into three levels: high risk, key responsibilities, and standard provisions.

                            **Output Format:**
                            Use Markdown with the following specific categories and emoji indicators. For each point, provide a brief, simple explanation.

                            **⚠️ High-Priority Clauses & Risks:**
                            *   Identify clauses related to significant financial penalties, liabilities, non-standard termination conditions, or automatic renewals that could be detrimental to the signer.

                            **📝 Key User Responsibilities:**
                            *   List specific actions, duties, or obligations the signer must perform to comply with the agreement (e.g., payment schedules, notice requirements, confidentiality rules).

                            **✅ Standard & Benign Provisions:**
                            *   List common, low-risk clauses (e.g., governing law, severability, force majeure) that are standard in such agreements.

                            **Document Text:**\n---\n{st.session_state.document_text}\n---\n**Categorized Analysis:**
                        """)

                        st.session_state.summary = get_gemini_response(model, summary_prompt)
                        st.session_state.risks = get_gemini_response(model, risks_prompt)
                        st.session_state.analysis_complete = True
                        st.session_state.messages = [] # Reset chat on new analysis
                    st.success("Analysis Complete!")
                else:
                    st.error("Failed to extract text. The PDF might be image-based or corrupted.")
            else:
                st.warning("Please upload a document first.")

    # --- Main Content Display ---
    if not st.session_state.analysis_complete:
        st.info("Upload your document and click 'Analyze Document' to see the results.")
    else:
        st.subheader("Analysis Results")
        
        col1, col2 = st.columns([1, 1.2]) # Giving more space to the detailed analysis
        with col1:
            st.markdown("#### 📝 Simple Summary")
            st.markdown(st.session_state.summary)

        with col2:
            st.markdown("#### 📊 Risk & Clause Breakdown")
            # Displaying the new categorized analysis directly without an expander
            st.markdown(st.session_state.risks)

        st.divider()

        # --- Chatbot Interface ---
        st.subheader("💬 Chat with Your Document")
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask a specific question (e.g., 'What is the late fee?')"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Searching for the answer..."):
                    # --- PROMPT 3: EDITED Smarter Q&A Prompt ---
                    qa_prompt = textwrap.dedent(f"""
                        **Role:** You are a helpful AI assistant for document analysis.

                        **Core Task:** Answer user questions based *exclusively* on the provided document text.

                        **Special Instructions for Safety/Opinion Questions:**
                        If the user asks for a legal opinion, or asks if the document is "safe," "fair," or "good," follow these steps:
                        1.  State clearly that you cannot provide legal advice.
                        2.  Explain that safety and fairness depend on individual circumstances and legal interpretation.
                        3.  Direct the user to review the "Risk & Clause Breakdown" for potential issues identified in the document.
                        4.  Recommend consulting a qualified legal professional for a definitive opinion.

                        **Standard Q&A Instructions:**
                        For all other factual questions:
                        1.  Locate the exact information in the document text.
                        2.  Provide the answer based only on that text.
                        3.  Cite the source by including a relevant quote, prefixed with "**Source:**".
                        4.  If the answer is not found, state: "I could not find an answer to your question in the provided document."

                        **Document Text:**\n---\n{st.session_state.document_text}\n---\n**User's Question:** "{prompt}"\n**Factual Answer:**
                    """)
                    response = get_gemini_response(model, qa_prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()