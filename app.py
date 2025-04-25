import streamlit as st
import numpy as np
import pickle
import joblib
import pandas as pd
import os

st.title("Student's Performance Checker")

file = open('performance.pkl', 'rb')
model = joblib.load(file)

# CSV file to store user history
HISTORY_FILE = 'user_history.csv'

# Collect user input
name = st.text_input("Your Name")
hr_std = st.number_input("Studied hour")
pr_scr = st.number_input("Previous score")
hr_slp = st.number_input("Sleep hours")
sp_ppr = st.number_input("No. of sample paper solved")
activi = st.radio('Activity',['Yes','No'])

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

        # Save to history
        new_entry = pd.DataFrame([{
            'Name': name,
            'Studied Hours': hr_std,
            'Previous Score': pr_scr,
            'Sleep Hours': hr_slp,
            'Sample Papers': sp_ppr,
            'Activity': activi,
            'Predicted Score': predicted_score
        }])

        if os.path.exists(HISTORY_FILE):
            history = pd.read_csv(HISTORY_FILE)
            history = pd.concat([history, new_entry], ignore_index=True)
        else:
            history = new_entry

        history.to_csv(HISTORY_FILE, index=False)

        # Show user-specific history
        user_history = history[history['Name'].str.lower() == name.lower()]
        if not user_history.empty:
            user_history = user_history.copy()

            if len(user_history) == 1:
                user_history['Status'] = 'Current'
            else:
                user_history['Status'] = 'Previous'
                user_history.loc[user_history.index[-1], 'Status'] = 'Current'

            cols = ['Status'] + [col for col in user_history.columns if col != 'Status']
            st.subheader("Your Prediction History:")
            st.dataframe(user_history[cols])

        # Optional: show total user count
        total_users = history['Name'].nunique()
        st.write(f"👥 Total unique users: {total_users}")

