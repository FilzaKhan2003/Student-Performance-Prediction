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
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
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
act_num_0 = 1 - act_num_1

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

                                
                if not history.empty:  
                    # 1. Find the best score for each student
                    best_scores = history.groupby('Name')['Predicted Score'].max().reset_index()

                    # 2. Sort them by score in descending order
                    best_scores = best_scores.sort_values(by='Predicted Score', ascending=False).reset_index(drop=True)

                    # 3. Assign Rank
                    best_scores['Rank'] = best_scores.index + 1

                    # 4. Show Top 5 Performers
                    st.subheader("🏆 Top Performers Leaderboard:")
                    st.table(best_scores.head(5))

                    # 5. Find the rank of the current user
                    user_rank = best_scores[best_scores['Name'].str.lower() == name.lower()]

                    if not user_rank.empty:
                        rank = int(user_rank['Rank'].values[0])
                        st.success(f"🎉 {name}, you're currently ranked #{rank}!")

                        # Check how much more to reach #1
                        top_score = best_scores['Predicted Score'].iloc[0]
                        your_best = user_rank['Predicted Score'].values[0]
                        diff = top_score - your_best

                        if diff > 0:
                            st.info(f"✨ Just {diff:.2f} more points to beat the top performer!")
                        else:
                            st.balloons()
                            st.success("🚀 Congratulations! You are the Top Performer!")

                    # Optional: show total user count
                    total_users = len(history['Name'].unique())
                    st.write(f"👥 Total unique users: {total_users}")
        
        except Exception as e:
            st.error(f"Error: {e}")
            st.error("Check that your Google Sheet has columns: Status, Name, Studied Hours, Previous Score, Sleep Hours, Sample Papers, Activity, Predicted Score")