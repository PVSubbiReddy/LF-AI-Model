import streamlit as st
import zipfile
import tempfile
import os
import pandas as pd
import ffmpeg
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication # Import for attaching CSV
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Load environment variables from .env file
load_dotenv()
email = os.getenv("EMAIL_USER")
password1 = os.getenv("EMAIL_PASSWORD")

def quality():
    """
    Main function for the Streamlit application to analyze agent call durations
    and generate/send reports.
    """

    def get_audio_duration(file_path):
        """
        Probes an audio file to get its duration using ffmpeg.
        Returns the duration in seconds (rounded to 2 decimal places) or None if an error occurs.
        """
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe['format']['duration'])
            return round(duration, 2)
        except ffmpeg.Error as e:
            # Catch ffmpeg specific errors for more targeted warnings
            st.warning(f"FFmpeg error processing {os.path.basename(file_path)}: {e.stderr.decode()}")
            return None
        except Exception as e:
            st.warning(f"Error reading {os.path.basename(file_path)}: {e}")
            return None

    def process_audio_folder(base_dir, rec_date):
        """
        Processes audio files within a given base directory, organizing data by agent.
        Uses ThreadPoolExecutor for parallel audio duration calculation.

        Args:
            base_dir (str): The base directory where the unzipped audio folders are located.
            rec_date (str): The recording date to check against file names.

        Returns:
            tuple: A pandas DataFrame with agent statistics, the count of unreadable files,
                   and a DataFrame of calls with duration > 180 seconds.
        """
        subfolders = [os.path.join(base_dir, name) for name in os.listdir(base_dir)
                      if os.path.isdir(os.path.join(base_dir, name))]

        if not subfolders:
            return pd.DataFrame(), 0, pd.DataFrame() # Return empty DataFrame for long calls too

        # Assuming the first subfolder is the root containing agent folders
        root_folder = subfolders[0]
        agent_data = []
        unreadable_count_total = 0
        all_long_calls_data = [] # To store data for calls > 180 seconds

        def process_agent_data(agent_name):
            """
            Processes a single agent's folder to gather audio file statistics.
            This function will be run in parallel for each agent.
            """
            agent_path = os.path.join(root_folder, agent_name)
            if not os.path.isdir(agent_path):
                return None, 0, [] # Return None for agent data, 0 unreadable, empty list for long calls

            durations = []
            file_count = 0
            valid_dates = 0
            invalid_dates = 0
            audio_files_to_process = [] # List to store file paths for parallel processing
            long_calls_for_agent = [] # To store long calls for the current agent

            for mobile_folder in os.listdir(agent_path):
                mobile_path = os.path.join(agent_path, mobile_folder)
                if not os.path.isdir(mobile_path):
                    continue
                for file in os.listdir(mobile_path):
                    file_path = os.path.join(mobile_path, file)
                    if file_path.lower().endswith(('.mp3', '.wav', '.m4a', '.flac', '.ogg')):
                        # Check date validity here before adding to processing list
                        if rec_date in file:
                            valid_dates += 1
                        else:
                            invalid_dates += 1
                        audio_files_to_process.append((file_path, mobile_folder)) # Store file_path and mobile_folder
                        file_count += 1

            current_agent_unreadable_count = 0
            # Use ThreadPoolExecutor to get durations in parallel for the current agent's files
            # Using a higher number of workers as ffmpeg.probe is I/O bound
            with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
                # Map get_audio_duration to all audio files and collect results
                # Use enumerate to keep track of the original file_path and mobile_folder
                results = executor.map(lambda x: get_audio_duration(x[0]), audio_files_to_process)
                for i, duration in enumerate(results):
                    original_file_path, mobile_num = audio_files_to_process[i] # Retrieve mobile_num
                    if duration is not None:
                        durations.append(duration)
                        # Check if duration is greater than 180 seconds
                        if duration > 180:
                            long_calls_for_agent.append({
                                'Agent_Name': agent_name,
                                'Mobile_Number': mobile_num, # Add mobile number here
                                'File_Name': os.path.basename(original_file_path),
                                'Duration(s)': duration # Include duration for context
                            })
                    else:
                        current_agent_unreadable_count += 1

            if durations:
                return {
                    "Agent_Name": agent_name,
                    "Total_Duration(s)": round(sum(durations), 0),
                    "Max_Duration(s)": round(max(durations), 0),
                    "Min_Duration(s)": round(min(durations), 0),
                    "Uploaded_Calls": file_count,
                    "Unique_Valid_Recs": valid_dates,
                    "Repeated_Unvalid_Recs": invalid_dates
                }, current_agent_unreadable_count, long_calls_for_agent
            return None, current_agent_unreadable_count, [] # Return empty list for long calls if no durations

        # Process each agent folder in parallel
        # Using os.cpu_count() for agent processing as it involves directory traversal and spawning sub-tasks
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            # Map process_agent_data to all agent names and collect results
            agent_results = executor.map(process_agent_data, os.listdir(root_folder))
            for agent_result, unreadable_count_for_agent, long_calls_for_agent in agent_results:
                if agent_result:
                    agent_data.append(agent_result)
                unreadable_count_total += unreadable_count_for_agent
                all_long_calls_data.extend(long_calls_for_agent) # Aggregate long calls from all agents

        return pd.DataFrame(agent_data), unreadable_count_total, pd.DataFrame(all_long_calls_data)

    def generate_html_report(df, rec_date):
        """
        Generates an HTML report from the agent performance DataFrame.

        Args:
            df (pd.DataFrame): DataFrame containing agent performance data.
            rec_date (str): The recording date for the report title.

        Returns:
            str: The complete HTML content of the report.
        """
        appender = ''
        desired_font_stack = "Calibri, Candara, Segoe, 'Segoe UI', Optima, Arial, sans-serif"

        for index, row in df.iterrows():
            text_color = 'black'
            if row['Uploaded_Calls'] <= 12:
                text_color = 'red'

            parser = f"""
                <tr>
                    <th scope="row" style="background-color:#f5e9f7; color: {text_color}; border-bottom: 1px solid #dcbae2;">{row['Agent_Name']}</th>
                    <td style="background-color:#f5e9f7; color: {text_color}; border-bottom: 1px solid #dcbae2;">{int(row['Uploaded_Calls'])}</td>
                    <td style="background-color:#f5e9f7; color: {text_color}; border-bottom: 1px solid #dcbae2;">{int(row['Total_Duration(s)'])}</td>
                    <td style="background-color:#f5e9f7; color: {text_color}; border-bottom: 1px solid #dcbae2;">{int(row['Max_Duration(s)'])}</td>
                    <td style="background-color:#f5e9f7; color: {text_color}; border-bottom: 1px solid #dcbae2;">{int(row['Min_Duration(s)'])}</td>
                </tr>"""
            appender += parser

        # Complete HTML template
        html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Agent Performance Report</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: {desired_font_stack};
                    margin: 0; /* Reset default body margin */
                    padding: 0;
                    background-color: #f0f4f8; /* Light background for the whole page */
                }}
                .container {{
                    max-width: 90%; /* Increased max-width for larger screens */
                    margin: 20px auto; /* Center the container with added vertical margin */
                    padding: 20px 30px;
                    background-color: #ffffff;
                    border-radius: 15px; /* Slightly more rounded container */
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); /* Refined shadow */
                    box-sizing: border-box; /* Include padding in width calculation */
                }}
                h1 {{
                    color: #7600BC; /* Modern primary color */
                    margin-bottom: 25px;
                    text-align: center;
                    font-weight: 600; /* Make heading bold */
                    border-bottom: 2px solid #e0e0e0; /* Add a subtle bottom border */
                    padding-bottom: 10px;
                }}
                p {{
                    margin-bottom: 15px;
                    line-height: 1.6; /* Improved line height for readability */
                    color: #555; /* Slightly darker text for better contrast */
                }}
                .alert {{
                    padding: 15px 20px;
                    margin-bottom: 20px;
                    border: 1px solid transparent;
                    border-radius: 10px; /* Rounded alert corners */
                    background-color: #f8ecfa; /* Light teal background for alerts */
                    color: #002b64; /* Darker teal text color */
                    border-color: #e2c3e7;
                    position: relative; /* For the icon positioning */
                    padding-left: 45px; /* Make space for the icon */
                }}
                .signature_bg {{
                    padding: 15px 20px;
                    margin-bottom: 20px;
                    border: 1px solid transparent;
                    border-radius: 10px; /* Rounded alert corners */
                    background-color: #d1ecf1; /* Light teal background for alerts */
                    color: #0c4085; /* Darker teal text color */
                    border-color: #b8daff;
                    position: relative; /* For the icon positioning */
                }}
                .alert-icon {{
                    position: absolute;
                    left: 15px;
                    top: 50%;
                    transform: translateY(-50%);
                    font-size: 20px; /* Increased icon size */
                    color: #007bff; /* Icon color matching the heading */
                }}
                .table-container {{
                    overflow-x: auto; /* Enable horizontal scrolling for tables on small screens */
                    margin-top: 20px;
                }}

                .styled-table {{
                    width: 100%;
                    border-collapse: collapse;
                    background-color: #ffffff;
                    border-radius: 10px; /* Rounded table corners */
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05); /* Very subtle table shadow */
                    overflow: hidden;  /* hide the overflowed part of rounded border */
                }}
                .styled-table thead tr {{
                    background-color: #a60fc4; /* Primary color for header */
                    color: white;
                    text-align: center;
                    font-weight: 500; /* Medium font weight for header text */
                }}
                .styled-table th, .styled-table td {{
                    padding: 14px 16px; /* Slightly increased padding */
                    text-align: center;
                    border-bottom: 1px solid #e0e0e0; /* Lighter border color */
                }}
                .styled-table th {{
                    font-weight: 600; /* Bold for header cells */
                }}
                .styled-table tbody tr:nth-child(odd) {{
                    background-color: #f9f9f9; /* Very light background for odd rows */
                }}
                .styled-table tbody tr:hover {{
                    background-color: #f0f0f0; /* Slightly darker hover */
                    transition: background-color 0.2s ease-in-out; /* Smooth transition */
                }}
                .red-text {{
                    color: red;
                    font-weight: 500; /* Medium font weight for important text */
                }}
                .signature {{
                    margin-top: 30px;
                    text-align: left;
                    font-style: italic;
                    color: #666;
                }}

                /* Responsive adjustments */
                @media screen and (max-width: 768px) {{
                    .container {{
                        padding: 15px;
                        width: 95%;
                    }}
                    .table-container {{
                        overflow-x: auto;
                    }}
                    .styled-table thead {{
                        display: none; /* Hide thead on small screens */
                    }}
                    .styled-table tr, .styled-table td {{
                        display: block;
                        text-align: right; /* Default text alignment for small screens */
                    }}
                    .styled-table td:before {{
                        content: attr(data-label); /* Show label before data */
                        float: left;
                        font-weight: 600;
                        margin-right: 10px;
                        color: #333; /* Label color */
                    }}
                    .styled-table td:first-child {{
                        border-top: 1px solid #e0e0e0; /* Add top border to the first cell in a row */
                    }}
                    #role {{
                        -webkit-text-stroke: 10px black;
                        text-stroke: 10px black;
                    }}
                }}
            </style>
            <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&icon_names=mail" />
        </head>
        <body>
            <div class="container">
                <h1>Call Upload Statistics - {rec_date}</h1>
                <p>Hi Sir,</p>
                <p>Please find the Call Upload Statistics - {rec_date} </p>
                <div class="alert">
                    <span class="alert-icon">⚠</span><br>
                    <b>Note for Quality Team:</b><br>
                    <ol>
                        <li>All the Red Marked Agent activity should be tracked.</li>
                    </ol>
                    <b>Note for Collections Team:</b>
                    <ol>
                        <li>Upload the Call Recording only after the followup.</li>
                        <li>Delete the Recording from mobile after uploading.</li>
                        <li>Don't upload the old call recording to increase the count.</li>
                    </ol>
                </div>
                <div class="table-container">
                    <table class="styled-table">
                        <thead>
                            <tr>
                                <th>Agent_Name</th>
                                <th>Uploaded_Calls</th>
                                <th>Total_Duration(s)</th>
                                <th>Max_Duration(s)</th>
                                <th>Min_Duration(s)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ....replacer....
                        </tbody>
                    </table>
                </div>
            </div>
            <div style="width: 600px; padding-top: 10px;" class="signature">
                <br><br>
                <h2>...</h2>
                <table cellpadding="0" cellspacing="0" style="width: 100%;">
                <tr>
                    <td style="padding: 0; margin: 0; width: 1px; vertical-align: bottom;">
                    <img src="https://ci3.googleusercontent.com/mail-sig/AIorK4xEi913O_BF582T-0H9pxp3E6fWBdn2M8wYdKLm5x3VCrwY136KO4FKYR_ypOKcWhbz47R80e7Ypk6c" alt="CapFront Logo" style="height: 80px; display: block; border: 0;margin-right: 10px;margin-bottom:4px;">
                    </td>


                    <td style="width: 1px; vertical-align: top; padding-top: 9px; padding-left: 1px;">
                    <div style="width: 1px; height: 92px; background-color: black; margin-top: 18px;"></div>
                    </td>

                    <td style="vertical-align: top; padding-left: 10px;padding-top: 15px;">
                    <div style="margin-bottom: 2px;  font-size: 10px;color:#0c4085;">Best Regards</div>
                    <div style="color: #001633; font-weight: bold; font-size: 13px; margin-bottom: 0px; font-family: Calibri;">
                        P. Venkata SUBBI REDDY</div>
                    <div style="margin-bottom: 8px; font-size: 11px;-webkit-text-stroke: 0.01px black; font-family: Calibri; color: rgb(255,176,1); font-weight: 800;">Team Lead - Ops Data Analyst
                    </div>

                    <div style="margin-bottom: 0px; font-family: Calibri; font-size: 11px; display: flex; align-items: center;">
                        <span style="margin-right: 5px; color: #001633; font-weight:600;font-family: Calibri Light;">
                        <img
                            src="https://ci3.googleusercontent.com/mail-sig/AIorK4y_lvmjayyfKoS8tXb_-G2obOy4iz7NOLcFnKbwzPycDwlERJI84x2nJXMqyEPM9i7-NamyrmytFMti"
                            alt="Phone" style="margin-bottom: -4px; ">
                        <span style="margin-left: -8px; color:#001633;">+91 9666014970</span>
                        </span>

                        <span style="margin-right: 5px; display: flex; width: fit-content;">
                        <img src='https://ci3.googleusercontent.com/mail-sig/AIorK4zFJLoEobKAlLNURPxwPO4G3n62LJGTTmId-gZNc6bEVG7ItufACyt_8F-JWLnxFGZHnGFbqZTE0UCq' style=" width: 13px; height: 9px; margin-top: 2px;"/>
                        <a href="mailto:subbi.reddy@vaibhav-vyapaar.com"
                            style="color: #001633;font-family: Calibri Light;font-size: 11px; margin-left: 6px;margin-bottom:4px;">subbi.reddy@vaibhav-vyapaar.com</a>
                        </span>

                        <span style="align-items: center; ">
                        <img
                            src="https://ci3.googleusercontent.com/mail-sig/AIorK4yX1DSnNlNjPfdWQZ8NLHBOsHszyGXd-aTx0ljjs2X9Q0EzlWFMKBhU5A1mCGoLAlKp05mul_TxUVRe"
                            alt="Website" style="height: 10px; vertical-align: middle;margin-right:-5px;">
                        <a href="https://www.vaibhav-vyapaar.com/" target="_blank"
                            style="color: #001633;font-family: Calibri Light;font-size: 11px; padding-bottom:5px; ">vaibhav-vyapaar.com</a>
                        </span>
                    </div>

                    <div
                        style="color: #001633; text-align: justify; font-size: 11px; line-height: 11px; font-family: Calibri Light; font-weight: 400;">
                        Second Floor, Envision Technology Centre, 119, Road No. 3, Phase-1,
                        Vijayanagar,<br> EPIP Zone, Whitefield, Bengaluru, Karnataka 560066, India.
                    </div>
                    </td>
                </tr>
                </table>

                <div
                style="font-size: 11px; font-family: 'Calibri'; margin-top: 10px; border-top: 1px solid #b8b8b8; padding-top: 1px; color: #333; text-align: justify; line-height: 11px;">
                <div style="border-top: 1px solid rgb(236, 236, 236); padding-top: 3px;">
                    <strong>DISCLAIMERS:</strong> This email and any files transmitted with it are confidential and intended solely
                    for the use of the individual or entity to whom they are addressed. This message contains confidential
                    information and is intended only for the individual named. If you are not the named addressee you should not
                    disseminate, distribute or copy this email. Please notify the sender immediately by email if you have received
                    this email by mistake and delete this email from your system.
                </div>
                </div>
            </div>
        </body>
        </html>
        """
        html_body = html_body.replace('....replacer....', appender)
        return html_body

    def send_email(html_content, recipients, rec_date, long_calls_df):
        """
        Sends an HTML email report to the specified recipients, with an attached CSV
        of calls longer than 180 seconds.

        Args:
            html_content (str): The HTML content of the email body.
            recipients (list): A list of email addresses to send the report to.
            rec_date (str): The recording date to be used in the email subject.
            long_calls_df (pd.DataFrame): DataFrame containing calls with duration > 180 seconds.
        """
        sender_name = "Subbi Reddy P"
        sender_email = email
        password = password1
        subject = f"Call Upload Statistics - {rec_date}(Test)"

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = ','.join(recipients)
        message["Subject"] = subject

        message.attach(MIMEText(html_content, "html"))

        # Attach the CSV for long calls if the DataFrame is not empty
        if not long_calls_df.empty:
            csv_data = long_calls_df.to_csv(index=False).encode('utf-8')
            attachment = MIMEApplication(csv_data, _subtype="csv")
            attachment.add_header('Content-Disposition', 'attachment', filename=f'long_calls_report_{rec_date}.csv')
            message.attach(attachment)
            st.success(f"CSV of long calls ({len(long_calls_df)} records) will be attached to the email.")
        else:
            st.info("No calls found with duration greater than 180 seconds to attach.")


        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, recipients, message.as_string())
            return True
        except Exception as e:
            st.error(f"Failed to send email: {e}")
            return False

    # Define recipients for the email report
    recipients = ["shivakumar.m@vaibhav-vyapaar.com"]
    # Uncomment and modify the following line to include more recipients
    # recipients = ["satya.mallidi@capfront.in","vinaya.k@capfront.in","shivakumar.m@vaibhav-vyapaar.com",
    #               "jeevitha.s@capfront.in",
    #               "ajith.m@vaibhav-vyapaar.com",
    #               "jyothieshwaran.m@vaibhav-vyapaar.com",
    #               "rahul.rathor@vaibhav-vyapaar.com",
    #               "ayesha.athiq@vaibhav-vyapaar.com",
    #               "priyadarshini.g@vaibhav-vyapaar.com"]

    # Streamlit UI
    st.title("📞 Agent Call Duration Analyzer")
    uploaded_file = st.file_uploader("Upload a ZIP file", type="zip")

    if uploaded_file:
        # Create a temporary directory to extract the zip file
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_file_name = uploaded_file.name
            # Extract recording date from the zip file name (assuming format like YYYY_MM_DD_...)
            rec_date = zip_file_name[:10].replace("_", "")
            zip_path = os.path.join(tmpdir, "uploaded.zip")

            # Write the uploaded file to the temporary directory
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.read())

            # Extract the zip file contents
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

            st.success("✅ ZIP file extracted successfully!")

            # Process the audio files and get the DataFrame, unreadable count, and long calls DataFrame
            df, unreadable_count, long_calls_df = process_audio_folder(tmpdir, rec_date)

            if not df.empty:
                # Sort the main DataFrame by 'Uploaded_Calls' in ascending order
                df = df.sort_values(by='Uploaded_Calls', ascending=True).reset_index(drop=True)

                st.subheader("📊 Agent Call Statistics")
                st.dataframe(df) # Display the DataFrame in Streamlit

                # Display long calls if any
                if not long_calls_df.empty:
                    st.subheader("⚠️ Calls with Duration > 180 Seconds")
                    st.dataframe(long_calls_df)
                    # Provide a download button for the long calls CSV
                    long_calls_csv = long_calls_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Long Calls CSV",
                        long_calls_csv,
                        f"long_calls_report_{rec_date}.csv",
                        "text/csv",
                        key='download-long-calls-csv'
                    )

                # Provide a download button for the main CSV report
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Full Report CSV",
                    csv,
                    f"agent_audio_summary_{rec_date}.csv", # Dynamic filename
                    "text/csv",
                    key='download-full-csv'
                )
                st.info(f"📂 {unreadable_count} file(s) could not be processed.")

                # Button to send the email report
                if st.button("📧 Send Email Report"):
                    # Generate HTML report
                    html_body = generate_html_report(df, rec_date)
                    # Send email and show success/failure message, passing the long_calls_df
                    if send_email(html_body, recipients, rec_date, long_calls_df):
                        st.success("📨 Report emailed successfully!")
                    else:
                        st.error("❌ Failed to send email report.")
            else:
                st.warning("⚠️ No valid audio files found or all files were unreadable in the uploaded ZIP.")