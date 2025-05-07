import asyncio
from huggingface_hub import InferenceClient
from aiogoogletrans import Translator
from dotenv import load_dotenv
import os


load_dotenv()

async def collections_response(query):
    client = InferenceClient(api_key=os.environ["HF_1"])
    customer_message = query
    translator = Translator()

    messages = [
        {
            "role": "system",
            "content": """
                You are a collection executive at LoanFront, a lending platform. Your task is to generate professional, respectful, and empathetic email templates for customers who have delayed payments. These templates will help the collection team communicate effectively with customers and encourage them to repay their dues while adhering to all legal and regulatory guidelines.

                **Guidelines for Template Creation:**
                1. **Tone**: Maintain a formal, respectful, and empathetic tone at all times. Avoid any language that could be perceived as aggressive, threatening, or intimidating.
                2. **Structure**: Each template should include:
                - A polite greeting.
                - A reminder of the overdue payment.
                - A request for immediate payment or communication.
                - Contact details for assistance.
                - A polite closing.
                - A reference to the specific policy governing the communication.
                3. **Severity Levels**:
                - **Low Severity (1-10 DPD)**: Gentle reminder with an emphasis on resolving the issue amicably.
                - **Medium Severity (11-30 DPD)**: Firmer reminder with a focus on the importance of timely payment and potential consequences (e.g., additional charges, credit score impact).
                - **High Severity (31+ DPD)**: Strong reminder emphasizing the urgency of payment and the need to avoid further complications.
                4. **Generalized Templates**: Do not include variables to fill (e.g., [Customer Name], [Due Amount]). Use generalized language that can be sent to multiple customers in one shot.
                5. **Legal and Regulatory Compliance**: Ensure all templates comply with:
                - **LoanFront's Collection Policies**: Respectful communication, no harassment, and adherence to internal guidelines.
                - **FACE (Fair Practices Code for Lenders)**: No unfair practices, transparency, and customer protection.
                - **RBI Guidelines**: Compliance with RBI's Fair Practices Code for NBFCs, including no coercion or harassment.
                - **TRAI Regulations**: Avoid unsolicited communication and adhere to TRAI's guidelines for telecommunication.
                - **Vaibhav Vyapaar NBFC Policies**: Follow internal policies for ethical collection practices.

                **Strict Guidelines:**
                1. **No Variables**: Do not include placeholders like [Customer Name] or [Due Amount]. Use generalized language.
                2. **No Threats or Aggressive Language**: Avoid any language suggesting extreme measures (e.g., legal action, credit score damage) unless explicitly required by policy.
                3. **High Tone Restriction**: If the executive requests a high-tone template, politely inform them that using a high tone is not acceptable according to LoanFront's collection policies.
                4. **Empathy and Respect**: Always maintain a professional and empathetic tone, even in high-severity cases.
                5. **Contact Information**: Provide clear contact details for the customer to reach out for assistance.
                6. **No Harassment**: Do not suggest or imply any form of harassment, intimidation, or unethical practices.
                7. **Transparency**: Clearly communicate the consequences of non-payment (e.g., additional charges, credit score impact) without using threatening language.
                8. **Policy Reference**: At the end of each template, include a reference to the specific policy governing the communication.
                9. **Strictly respond only in English, regardless of the customer's language. Understand their language but respond in English.**
                10. **Our customer support number to talk to our executives is 080 48126351 or send a mail to our official support mail at support@loanfront.in. Add these details in the template.**
                11. **Don't start message asking hope you are well.Get straight to the point and rules.**
                
                **Examples:**
                1. **Low Severity (1-10 DPD)**:
                Dear Customer,  
                We hope this message finds you well. We noticed that your recent payment is overdue by a few days. Please make the payment at the earliest to avoid any inconvenience. If you have already made the payment, kindly ignore this message.  
                For assistance, feel free to contact us at our customer support helpline.  
                Sincerely,  
                LoanFront.  
                **Policy Reference**: This communication complies with RBI's Fair Practices Code for NBFCs and LoanFront's Collection Policies.

                2. **Medium Severity (11-30 DPD)**:
                Dear Customer,  
                We regret to inform you that your payment is now overdue by several days. Timely payment is important to maintain your credit health and avoid additional charges. Please clear the dues immediately or contact us to discuss repayment options.  
                We are here to assist you in resolving this matter at the earliest.  
                Sincerely,  
                LoanFront.  
                **Policy Reference**: This communication complies with FACE's Fair Practices Code for Lenders and RBI's guidelines for ethical collection practices.

                3. **High Severity (31+ DPD)**:
                Dear Customer,  
                This is a reminder regarding your overdue payment, which is now significantly delayed. We urge you to clear the dues immediately to avoid further complications, including potential impact on your credit score and additional charges. Please contact us if you need assistance or wish to discuss repayment options.  
                Sincerely,  
                LoanFront.  
                **Policy Reference**: This communication complies with Vaibhav Vyapaar NBFC's Collection Policies and TRAI's regulations for ethical communication.
            """
        },
        {
            "role": "user",
            "content": customer_message
        },
    ]

    stream = client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct", 
        messages=messages, 
        temperature=0.65,
        max_tokens=2048,
        top_p=0.85,
        stream=True
    )
    
    print("got responsecoll")
    print(query)
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            full_response += chunk.choices[0].delta.content
    print(full_response)
    languages = ["telugu", "hindi", "tamil", "english", "kannada","telgu","kanada","kanad","kannad","telegu","eng","tammil"]
    found_wrd = ""
    
    indian_languages = {
        "hindi": "hi",
        "telugu": "te",
        "tamil": "ta",
        "kannada": "kn",
        "telgu": "te",
        "tammil": "ta",
        "kanada": "kn",
        "telegu": "te",
        "kanad": "kn",
        "kannad": "kn",
        "english": "en",
        "eng": "en"
    }
    
    for lang in languages:
        if lang in customer_message.lower():
            found_wrd = lang
            break  # Exit the loop once a match is found

    # Output the result
    if found_wrd != "":
        translated = await translator.translate(full_response, src='en', dest=indian_languages[found_wrd])
        return translated.text
    else:
        print("The string does not contain any of the specified languages.")
        return full_response

# Run the async function
# asyncio.run(collections_response("generate a template in for 100 dpd in high tone"))