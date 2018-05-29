import requests
import pandas as pd
from twilio.rest import Client
import pytz
from dotenv import load_dotenv, find_dotenv
import os


load_dotenv(find_dotenv())

global SEND_NOSTORM_TEXT
SEND_NOSTORM_TEXT = False


def get_twilio():
    """Get a twilio client"""
    return Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_AUTH"))


def send_sms(client, text):
    """Send a text message with the given client and string"""
    client.messages.create(from_=os.getenv("TWILIO_PHONE_NUMBER"),
                           to=os.getenv("MY_PHONE_NUMBER"),
                           body=text)


def get_noaa():
    """
    Get the noaa planetary k-index forecast
    the request returns json text containing:
    time, kp, observered/estimated, noaa scale
    """

    forecast_json = requests.get(os.getenv("NOAA_URL")).json()[1:-1]  # Cut out the first row, it contains the header.

    framed_json = list()
    for i in forecast_json:
        framed_json.append(i[0:-1])  # Get just the first three columns, the last one is not needed

    forecast_df = pd.DataFrame(data=framed_json, columns=['time (UTC)', 'kP', 'observed'])
    forecast_df['kP'] = forecast_df[['kP']].apply(pd.to_numeric)  # Set the dtype of kP to numeric
    forecast_df['time (UTC)'] = forecast_df[['time (UTC)']].apply(pd.to_datetime)  # Set the dtype of time to datetime
    forecast_df = forecast_df.set_index('time (UTC)')
    forecast_df['time (CST)'] = forecast_df.index.tz_localize(pytz.utc).tz_convert(pytz.timezone('US/Central'))  # Update time from UTC to CST
    forecast_df['time (CST)'] = forecast_df['time (CST)'].dt.strftime('%B %d, %Y, %r')
    predicted = forecast_df.loc[forecast_df['observed'] == 'predicted']  # Get only the predicted rows
    return predicted


def storm_notification(data):
    geostorm = data.loc[data['kP'] >= 5]
    if not geostorm.empty:
        notification = "NOAA data is predicting high kP values at the following times:\n"
        storms = 0
        for _, row in geostorm.iterrows():
            notification += "{time} CST: \t{}kP\n".format( str(row['kP']), time=str(row['time (CST)']))
            storms += 1
        if storms:
            send_sms(get_twilio(), notification)
    elif SEND_NOSTORM_TEXT:
        send_sms(get_twilio(), "No high kP values are predicted for the upcoming days")

if __name__ == "__main__":
    data = get_noaa()
    storm_notification(data)
