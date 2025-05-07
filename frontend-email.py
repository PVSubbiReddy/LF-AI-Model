import streamlit as st
from email_draft_v2 import response
from collections_help import collections_response
from general_topics import general_response
import os
import base64
import asyncio


def load_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

# Provide the path to your image
image_path = os.path.join("images", "favicon.png")
base64_image = load_base64_image(image_path)

st.set_page_config(
    page_title="LoanFront Support Assistant",
    page_icon="images/favicon.png",  # Replace with the path to your PNG file
    layout="wide"
)

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
selected_option = st.sidebar.selectbox("Choose a module:", options, index=0)

# LoanFront Title and Description
st.markdown(
    f"""
    <h1>
        <img src="data:image/png;base64,{base64_image}" style="width:35px; vertical-align:middle; margin-right:10px;">
        LoanFront Support Assistant<sup style="font-size: 0.6em; vertical-align: super;">&nbsp[Beta]</sup>
    </h1>
    """,
    unsafe_allow_html=True
)

# Password mapping for categories
passwords = {
    "Collections": "Vai@321",
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
        
        
common_prompts = """
2) As these responses are created by the AI Bot, please cross-verify the content before using it in real cases.
<br>3) This bot is bound only towards LoanFront policies, so don't use it for external purposes.
<br>4) All the requests and responses will be tracked and traced. So use it wisely.
<br>5) Please ensure that you stay within the allocated daily credits limit, as we provide limited control over its usage.
"""

# Display category-specific content
if selected_option in ["General Inquiries","Leave Policies","Strategy Building For Recovery","Posh Policies"]:
    st.markdown(
        f"""Welcome to the LoanFront Support Assistant. You can resolve your {selected_option} here. <br><br>
        Example:- Generate a response to this message <span style='color:#FFE100;-webkit-text-stroke: 0.0090px black;'>**"Hi iam waiting for your response regarding my leave request.**"</span>
        <br><br>
        Note: 
        <br>1) You can use this module only for General Inquiries. Please change the category for a different one.<br>{common_prompts}"""
        ,unsafe_allow_html=True
    )
elif selected_option == "Email Support" and authenticated:
    st.markdown(
        f"""Welcome to the LoanFront Support Assistant. You can generate {selected_option} templates here. <br><br>
        How to use :- <br>
        <span style='color:#FFE100;-webkit-text-stroke: 0.0090px black;'>
        ▲ Paste the customer mail body in the prompt box, you will get the response template.<br>
        ▲ Example:- "i will pay later", ask customer to provide required proofs for extension.(you will get response accordingly) </span>
        <br><br>
        Note: 
        <br>1) You can use this module only for {selected_option} related queries in the way as mentioned above. Please change the category for a different one.<br>{common_prompts}"""
        ,unsafe_allow_html=True
    )
elif selected_option == "Collections" and authenticated:
    st.markdown(
        f"""Welcome to the LoanFront Support Assistant. You can generate {selected_option} templates here. <br><br>
        How to use :- <br>
        <span style='color:#FFE100;-webkit-text-stroke: 0.0090px black;'>
        * Example:- Generate a template for 23 DPD customer who is giving fake commitments daily.<br>
        * Example:- Customer is not at all ready to pay even after 3 months, how can i convince him? </span>
        <br><br>
        Note: 
        <br>1) You can use this module only for {selected_option} related queries in the way as mentioned above. Please change the category for a different one.<br>{common_prompts}"""
        ,unsafe_allow_html=True
    )
elif selected_option == "Quality" and authenticated:
    st.markdown(
        f"""Welcome to the LoanFront Support Assistant. You can generate {selected_option} suggestions here. <br><br>
        How to use :- <br>
        * Example :- agent is not saying NBFC name, is it an error and how to raise it?<br>
        * Example:- agent is talking harshly to the customer, is it an error if yes how to raise it 
        <br><br>
        Note: 
        <br>1) You can use this module only for {selected_option} related queries in the way as mentioned above. Please change the category for a different one.<br>{common_prompts}"""
        ,unsafe_allow_html=True
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
                        responses = asyncio.run(collections_response(clean_query))
                    elif selected_option == "General Inquiries":
                        responses = asyncio.run(general_response(clean_query))
                    elif selected_option == "Email Support":
                        responses = response(clean_query)
                    elif selected_option == "Quality":
                        responses = f"Quality-related response for: {clean_query}"  # Placeholder logic
                        
                    st.markdown("### Response:")
                    st.write(responses)
                    
                    # Copy button (optional functionality to copy response)
                    if responses:
                        pass
                except Exception as e:
                    st.error(f"Error generating response: {e}")
        else:
            st.warning("Please enter a query before submitting.")

st.markdown("---")
st.markdown("""Powered by <span style='color:#FFE100;-webkit-text-stroke: 0.0090px black;'>LoanFront AI.</span>""",unsafe_allow_html=True)
