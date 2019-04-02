#-- Climate App
#
# April 2, 2019
# Scott McEachern

#-- Application Info
print("Starting climate Flask app")
print(" ")


#-- Import Dependency
from flask import Flask, jsonify

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func, inspect

import datetime as dt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import numpy as np


#-- Setup Database
#  Added check same thread due to errors when deployed to Flask; accessing SQLite on different thread
print("--> Setup Database")
print("Preparing database connection")
engine = create_engine("sqlite:///Resources/hawaii.sqlite", connect_args={'check_same_thread': False})

#- Reflect the Tables
Base = automap_base()
Base.prepare(engine, reflect=True)

#- Reference Tables
print("Referencing tables")
Measurement = Base.classes.measurement
Station = Base.classes.station

#- Create Session
print("Creating session with database")
session = Session(engine)


#-- Create App
print("--> Create Flask App")
app = Flask(__name__)

print("Completed setting up app")


#-- Flask Routes
@app.route("/")
def home():
    ''' Home Page: returns list of the available routes for the app
    '''

    print(" ")
    print("--> Home")


    availableRoutes = {
        "Precipitation": '/api/v1.0/precipitation',
        'Stations': 'api/v1.0/stations',
        'tobs': '/api/v1.0/tobs',
        'temperatureRange': '/api/v1.0/<start>/<end>',
        'temperatureFromStart': '/api/v1.0/<start>'
    }
    

    return jsonify(availableRoutes)


@app.route("/api/v1.0/precipitation")
def precipitation():
    ''' Returns the precipitation found in the database

    Accepts : none

    Returns : JSON - date as key and prcp as the value
    '''

    print(" ")
    print("--> Precipition")

    #-- Determine Start Date
    #- Last date in dataset
    lastDateString = session.query(func.max(Measurement.date)).scalar()

    #- Convert to DateTime from String
    lastDate = datetime.strptime(lastDateString, '%Y-%m-%d')

    #- 12 Months from last date
    startDate = lastDate - relativedelta(years=1)

    print(f"Determined date range, Start: {startDate}  End: {lastDate}")


    #-- Get Records from Database
    sel = [Measurement.date,
            Measurement.prcp]

    records = session.query(*sel).filter(Measurement.date.between(startDate, lastDate)).all()

    print(f"Success in querying records from database; total records: {len(records)}")


    #-- Convert to Dictionary where date is key and prcp
    recordDictionary = {}

    for record in records:
        recordDictionary[record[0]] = record[1]


    #-- Return Records
    return jsonify(recordDictionary)


@app.route("/api/v1.0/stations")
def stations():
    ''' Returns list of the stations found within the database

    Accepts : none

    Returns: JSON - List of stations that are dictionary with station, name, latitude and longitude
    '''

    print(" ")
    print("--> Stations")


    #-- Get Records from Database
    select = [
        Station.station, 
        Station.name, 
        Station.latitude,
        Station.longitude
    ]

    stationRecords = session.query(*select).all()

    print(f"Completed getting records from database. Total: {len(stationRecords)}")


    #-- Prepare List of Stations
    stationResult = []

    for stationRecord in stationRecords:
    
        stationResult.append({
            "id": stationRecord[0],
            "name": stationRecord[1],
            "latitude": stationRecord[2],
            "longitude": stationRecord[3]
        })

    print("Completed transformation of station information")

    return jsonify(stationResult)


@app.route("/api/v1.0/tobs")
def tobs():
    ''' Return the last year of temperature observations

    Accepts : none

    Returns : JSON - list of observations that are dictionary with tobs, date, station
    '''

    print(" ")
    print("--> tobs")


    #-- Determine Start Date
    #- Last date in dataset
    lastDateString = session.query(func.max(Measurement.date)).scalar()

    #- Convert to DateTime from String
    lastDate = datetime.strptime(lastDateString, '%Y-%m-%d')

    #- 12 Months from last date
    startDate = lastDate - relativedelta(years=1)

    print(f"Determined date range, Start: {startDate}  End: {lastDate}")

    
    #-- Query Observations from Database
    select = [
        Measurement.tobs,
        Measurement.date,
        Measurement.station
    ]

    records = session.query(*select).filter(Measurement.date.between(startDate, lastDate)).all()

    print(f"Completed getting records from database; total records: {len(records)}")


    #-- Prepare List of Observations
    observations = []

    for record in records:
        observations.append({
            "tobs": record[0],
            "date": record[1],
            "station": record[2]
        })
    
    print("Completed preparing list of observations")


    return jsonify(observations)


@app.route('/api/v1.0/<start>/<end>')
def temperatureRange(start, end):
    ''' Determines min/max/average temperature for the date range provided

    Accepts : start (str) date to start the query of records, format of "yyyy-mm-dd"
              end (str) date to end the query of records, format of "yyyy-mm-dd"

    Returns : JSON with attributes of avetemp, maxtemp, mintemp

    '''

    print(" ")
    print("--> Temperature Range")

    
    #-- Get Start Date
    print(f'Determine start date: {start}')

    try:
        startDate = datetime.strptime(start, '%Y-%m-%d')
    except:
        return jsonify({'error': f'Error encountered converting start date provided, not in correct format (yyyy-mm-dd). Value: {start}'}), 400

    print(f'Converted parameter to start date: {startDate}')


    #-- Get End Date
    print(f'Determine end date: {end}')

    try:
        endDate = datetime.strptime(end, '%Y-%m-%d')
    except:
        return jsonify({'error': f'Error encountered converting end date provided, not in correct format (yyyy-mm-dd). Value: {end}'}), 400

    print(f'Converted parameter to end date: {endDate}')


    #-- Calculate Temperature Info
    return jsonify(calculateTemperateInfo(startDate, endDate))


@app.route('/api/v1.0/<start>')
def temperatureFromStart(start):
    ''' Determines min/max/average temperature that are greater than and equal to the start date provided

    Accepts : start (str) date to start the query of records, format of "yyyy-mm-dd"

    Return : JSON with attributes of avetemp, maxtemp, mintemp
    '''

    print(" ")
    print("--> Temperature From Start")


    #-- Get Start Date
    print(f'Determine start date: {start}')

    try:
        startDate = datetime.strptime(start, '%Y-%m-%d')
    except:
        return jsonify({'error': f'Error encountered converting start date provided, not in correct format (yyyy-mm-dd). Value: {start}'}), 400

    print(f'Converted parameter to start date: {startDate}')


    #-- Determine end date in dataset
    endDateString = session.query(func.max(Measurement.date)).scalar()

    endDate = datetime.strptime(endDateString, '%Y-%m-%d')

    print(f"Determine end date of dataset; {endDate}")


    #-- Calculate Temperature Info
    return jsonify(calculateTemperateInfo(startDate, endDate))


def calculateTemperateInfo(startDate, endDate):
    ''' Determines temperation information based on the date range provided

    Accepts : startDate (date) begin of date range
              endDate (date) end of date range

    Returns : dictionary; mintemp, avetemp, maxtemp
    '''

    #- Query Database
    results = session.query(func.min(Measurement.tobs), func.avg(Measurement.tobs), func.max(Measurement.tobs)).\
        filter(Measurement.date.between(startDate, endDate)).all()

    return {
        'mintemp': results[0][0],
        'avetemp': results[0][1],
        'maxtemp': results[0][2]
    }



    