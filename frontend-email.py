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
st.markdown(
    """
    <h1>LoanFront Support Assistant<sup style="font-size: 0.6em; vertical-align: super;">[Beta]</sup></h1>
    """,
    unsafe_allow_html=True
)

# Password mapping for categories
passwords = {
    "Collections": "Cap@321",
    "Email Support": "Vai@123",
    "Quality": "Lf@54321"
}

# Check if the category is password-protected
password_protected = selected_option in passwords
authenticated = False

if password_protected:
    password = st.text_input(f"Enter the password to access the '{selected_option}' module:", type="password")
    if password == passwords[selected_option]:
        authenticated = True
    elif password:
        st.error("Incorrect password. Please try again.")

# Display category-specific content
if selected_option == "General Inquiries":
    st.markdown(
        """Welcome to the LoanFront Support Assistant. You can resolve your general doubts here. <br><br>
        Example:- Generate a response to this message <span style='color:Yellow'>**"Hi iam waiting for your response regarding my leave request.**"</span>
        <br><br>
        Note: 
        <br>1) You can use this module only for General Inquiries. Please change the category for a different one.
        <br>2) As these responses are created by the AI Bot, Please cross verify the content before using it in real case.
        <br>3) This bot is binded only towards LoanFront policies, so don't use it for external purposes.
        <br>4) All the requests and responses will be tracked and traced. So use it wisely.
        <br>5) Please ensure that you stay within the allocated daily credits limit, as we provide limited control over its usage."""
        ,unsafe_allow_html=True
    )
elif selected_option in passwords and authenticated:
    st.markdown(
        f"Welcome to the LoanFront Support Assistant. Enter your query below and get professional responses related to {selected_option.lower()} templates."
    )
elif selected_option in passwords and not authenticated:
    st.warning(f"Authentication is required to access the '{selected_option}' category. Please enter the correct password.")

# Input text area and form for auto-submit on "Enter"
if not password_protected or authenticated:
    with st.form(key="query_form"):
        user_query = st.text_area(
            "Enter your query:", 
            placeholder=f"Type your {selected_option.lower()}-related question here...",
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
                    elif selected_option == "Quality":
                        responses = f"Quality-related response for: {clean_query}"  # Placeholder logic
                        
                    st.markdown("### Response:")
                    st.write(responses)
                    
                    # Copy button (optional functionality to copy response)
                    if responses:
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
