import streamlit as st
from email_draft_v2 import response
from collections_help import collections_response

st.set_page_config(page_title="LoanFront Chatbot", page_icon="📈", layout="wide")

# Sidebar with categories
st.sidebar.title("LoanFront")  
options = [
    "General Inquiries", 
    "Collections", 
    "Leave Policies", 
    "Strategy Building For Recovery", 
    "Posh Policies", 
    "Email Support", 
    "Quality"
]
selected_option = st.sidebar.selectbox("Choose a category:", options, index=0)

# LoanFront Title and Description
st.title("LoanFront Support Assistant")
st.markdown(
    "Welcome to the LoanFront Support Assistant. Enter your query below and get professional responses related to loan services."
)

# Input text area and form for auto-submit on "Enter"
with st.form(key="query_form"):
    user_query = st.text_area(
        "Enter your query:", 
        placeholder="Type your loan-related question here...",
        height=150
    )
    submit_button = st.form_submit_button(label="Get Response")

# Process query and generate response
if submit_button:
    if user_query.strip():
        # Normalize newlines by removing unnecessary blank lines
        clean_query = "\n".join([line.strip() for line in user_query.splitlines() if line.strip()])
        
        with st.spinner("Generating response..."):
            try:
                responses = None
                if selected_option == "Collections":
                    responses = collections_response(clean_query)
                elif selected_option == "Email Support":
                    responses = response(clean_query)
                    
                st.markdown("### Response:")
                st.write(responses)
                
                # Copy button (optional functionality to copy response)
                if responses:
                    # st.button("📋 Copy to Clipboard", key="copy_button", on_click=st.form_submit_button(label="Get Response"))
                    st.markdown("\n")
                    st.markdown("***")
                    st.markdown("Click on 'Get Response' button to get fresh template")
                    pass
            except Exception as e:
                st.error(f"Error generating response: {e}")
    else:
        st.warning("Please enter a query before submitting.")

st.markdown("---")
st.markdown("Powered by LoanFront AI.")
