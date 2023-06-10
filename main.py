from __future__ import print_function
import datetime

from flask import Flask, render_template, redirect

import os.path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import json
from itertools import groupby
from dateutil.parser import parse
from datetime import date

from google.oauth2 import service_account

from session import Session

app = Flask(__name__)

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1G_PQnL3uo82JriCAADN0UntO9LxSXUMTL3sXGQpE3j8'
SAMPLE_RANGE_NAME = '!A2:G'

def parse_session_date(date_str):
	return parse(date_str, fuzzy=True).date()

def get_data():
    creds = None
    with open('credentials.json') as source:
        info = json.load(source)
        creds = service_account.Credentials.from_service_account_info(info)

    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        values = result.get('values', [])

        if not values:
            print('No data found.')
            return []

        return [
            {
            "bookedBy": v[1],
            "bookingDate": v[0],
            "session": Session(v[2], parse_session_date(v[2])),
            "boat": v[3],
            "preferredPosition": v[4],
            "notes": v[6] if len(v) >= 7 else ""
            } for v in filter(lambda b: b, values)
        ]
    except HttpError as err:
        if (err.status_code == 429):
            app.logger.info('Hit rate limit')
            raise Exception('Rate limit has been reached. Please wait a few minutes before retrying.')
        print(err)

def get_data_for_date(session_date, bookings):
	return list(filter(lambda b: b.get('session').date == session_date, bookings))

def groupby_boat_type(bookings):
    sorted_bookings = sorted(bookings, key=lambda b: b.get('boat'))
    boat_bookings = groupby(sorted_bookings, lambda b: b.get('boat'))
    return {boat: list(it) for (boat, it) in boat_bookings}

def extract_sessions(bookings):
	return sorted(
             set([booking.get('session') for booking in bookings]), 
             key=lambda session: session.date
    )

def future_sessions(sessions):
     return filter(lambda session: session.date >= date.today(), sessions)

@app.route('/')
def root():
    return redirect("/today")

@app.route('/all')
def all():
    bookings = get_data()
    return render_template('index.html', 
        bookings=groupby_boat_type(bookings), 
        sessions=future_sessions(extract_sessions(bookings)))

@app.route('/today')
def today():
    try:
        bookings = get_data()
        return render_template('index.html', 
        	bookings=groupby_boat_type(get_data_for_date(date.today(), bookings)), 
        	sessions=future_sessions(extract_sessions(bookings)), 
            date=str(date.today()))
    except Exception as ex:
        raise ex

@app.route('/date/<session_date>')
def specific_date(session_date):
    try:
        bookings = get_data()
        the_date = parse(session_date).date()
        return render_template('index.html', 
        	bookings=groupby_boat_type(get_data_for_date(the_date, bookings)), 
        	sessions=future_sessions(extract_sessions(bookings)), 
            date=str(the_date))
    except Exception as ex:
        raise ex


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)