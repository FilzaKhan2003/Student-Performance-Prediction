import streamlit as st
import numpy as np
import pickle
import joblib
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import os

# Google Sheets API setup using Streamlit secrets
def authenticate_gspread():
    try:
        # Get credentials from Streamlit secrets
        credentials_dict = st.secrets["gcp_service_account"]
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_dict(credentials_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Authentication error: {e}")
        st.error("Make sure your Streamlit secrets are properly configured with GCP service account credentials.")
        return None

def append_to_google_sheet(sheet_name, data):
    client = authenticate_gspread()
    if client:
        try:
            # Open your Google Sheet
            sheet = client.open(sheet_name).sheet1
            sheet.append_row(data)
            return True
        except Exception as e:
            st.error(f"Error accessing Google Sheet: {e}")
            return False
    return False

# Streamlit app code
st.title("Student's Performance Checker")

try:
    file = open('performance.pkl', 'rb')
    model = joblib.load(file)
except Exception as e:
    st.error(f"Error loading model: {e}")
    st.stop()

# Collect user input
name = st.text_input("Your Name")
hr_std = st.number_input("Studied hour")
pr_scr = st.number_input("Previous score")
hr_slp = st.number_input("Sleep hours")
sp_ppr = st.number_input("No. of sample paper solved")
activi = st.radio('Activity', ['Yes', 'No'])

act_num_1 = 1 if activi == "Yes" else 0
act_num_0 = 0 if activi == "No" else 1

input_data = np.array([hr_std, pr_scr, hr_slp, sp_ppr, act_num_0, act_num_1])

if st.button("Check Performance"):
    if name.strip() == "":
        st.error("⚠️ Please enter your name before proceeding.")
    else:
        prediction = model.predict([input_data])
        predicted_score = round(prediction[0], 2)
        st.success(f"🎯 Predicted Score: {predicted_score}")

        # Save to Google Sheet with "Current" status for the new entry
        new_entry = ["Current", name, hr_std, pr_scr, hr_slp, sp_ppr, activi, predicted_score]
        
        try:
            # First, update any existing entries for this user to "Previous"
            client = authenticate_gspread()
            if client:
                sheet = client.open('User History').sheet1
                all_rows = sheet.get_all_values()
                
                # Get the header row and find column indices
                headers = all_rows[0]
                status_idx = headers.index("Status")
                name_idx = headers.index("Name")
                
                # Update previous entries for this user to "Previous"
                for i, row in enumerate(all_rows[1:], start=2):  # Start from 2 because sheet rows are 1-indexed and we skip header
                    if row[name_idx].lower() == name.lower() and row[status_idx] == "Current":
                        sheet.update_cell(i, status_idx + 1, "Previous")  # +1 because gspread is 1-indexed
                
                # Now append the new entry
                if append_to_google_sheet('User History', new_entry):
                    st.success("Data saved to Google Sheet successfully!")
                
                # Reload the data to show updated history
                history_data = sheet.get_all_records()
                history = pd.DataFrame(history_data)
                
                # Ensure all columns are properly typed
                if 'Name' in history.columns:
                    history['Name'] = history['Name'].astype(str)
                
                # Filter for this user's history
                user_history = history[history['Name'].str.lower() == name.lower()]
                
                if not user_history.empty:
                    st.subheader("Your Prediction History:")
                    st.dataframe(user_history)
                    
                    # Show improvement if multiple entries exist
                    if len(user_history) > 1:
                        current_score = user_history[user_history['Status'] == 'Current']['Predicted Score'].values[0]
                        previous_scores = user_history[user_history['Status'] == 'Previous']['Predicted Score'].values
                        if len(previous_scores) > 0:
                            latest_previous = previous_scores[-1]
                            improvement = current_score - latest_previous
                            if improvement > 0:
                                st.success(f"📈 You've improved by {improvement:.2f} points since your last prediction!")
                            elif improvement < 0:
                                st.warning(f"📉 Your predicted score has decreased by {abs(improvement):.2f} points since last time.")
                            else:
                                st.info("Your predicted score is the same as last time.")

                # Optional: show total user count
                total_users = len(history['Name'].unique())
                st.write(f"👥 Total unique users: {total_users}")
        
        except Exception as e:
            st.error(f"Error: {e}")
            st.error("Check that your Google Sheet has columns: Status, Name, Studied Hours, Previous Score, Sleep Hours, Sample Papers, Activity, Predicted Score")