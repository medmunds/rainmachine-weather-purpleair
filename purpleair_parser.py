# purpleair_parser.py
# Custom PurpleAir weather service for RainMachine
# Released under the MIT License
# https://github.com/medmunds/rainmachine-weather-purpleair/LICENSE

import time
import sys

from RMParserFramework.rmParser import RMParser
from RMUtilsFramework.rmLogging import log

import json


PROJECT = "rainmachine-weather-purpleair"
VERSION = "0.1"
ABOUT_URL = "https://github.com/medmunds/rainmachine-weather-purpleair"

log.info("Loaded %s v%s", PROJECT, VERSION)

# Older RainMachine models (e.g., Mini-8) have outdated root certificates,
# which don't work with https://www.purpleair.com. Fall back to http for them.
USE_HTTPS = sys.version_info >= (2, 7, 12)
if not USE_HTTPS:
    log.info("Falling back to http due to outdated platform")

# Identify ourself when querying PurpleAir's API
USER_AGENT = "{project}/{version} ({about_url})".format(project=PROJECT, version=VERSION, about_url=ABOUT_URL)


class PurpleAir(RMParser):
    parserName = "PurpleAir Parser"
    parserDescription = "Obtain temperature from PurpleAir sensor"
    parserForecast = False
    parserHistorical = True
    parserInterval = 60 * 60  # seconds (no point reporting more than once an hour)
    parserDebug = False
    purpleAirUrl = "%s://www.purpleair.com/json" % ("https" if USE_HTTPS else "http")
    params = {
        "sensorId": None,
        "keyForPrivateSensor": None,
    }
    defaultParams = {
        "sensorId": None,
        "keyForPrivateSensor": None,
    }
    maxAgeMinutes = 60  # ignore data older than this

    def isEnabledForLocation(self, timezone, lat, long):
        return self.parserEnabled

    def perform(self):
        sensor_id = self.params.get("sensorId", None)
        if not sensor_id:
            # TBD: could probably query nearby PurpleAir sensors
            #   based on self.settings.location.latitude and .longitude
            self.lastKnownError = "must set PurpleAir sensorId"
            log.error(self.lastKnownError)
            return

        api_key = self.params.get("keyForPrivateSensor", None)

        data = self.fetch_sensor_data(sensor_id, api_key)
        if data is not None:
            cleaned = self.clean_sensor_data(data)
            if cleaned is not None:
                self.add_sensor_data(cleaned)

    def fetch_sensor_data(self, sensor_id, api_key=None):
        params = {"show": sensor_id}
        if api_key:
            # Key is only required to access private sensors
            params["key"] = api_key
        response = self.openURL(self.purpleAirUrl, params, headers={"user-agent": USER_AGENT})
        if response is None:
            # For errors from urllib2.urlopen, openURL logs the actual error,
            # sets lastKnownError to generic "Error: Can not open url",
            # and returns None. Improve that error (slightly):
            self.lastKnownError = "error querying PurpleAir sensor '%s'; check logs" % sensor_id
            log.error(self.lastKnownError)
            return None

        body = response.read()
        try:
            data = json.loads(body)
        except ValueError as err:
            self.lastKnownError = "error loading json response"
            log.exception(self.lastKnownError, exc_info=err)
            return None
        else:
            log.info("data retrieved for sensor %s", sensor_id)
            return data

    def clean_sensor_data(self, data):
        # For a multi-sensor PurpleAir device, the first result includes temperature, etc.
        try:
            result = data["results"][0]
        except KeyError as err:
            self.lastKnownError = "unexpected response format"
            log.exception(self.lastKnownError, exc_info=err)
            return None
        except IndexError:  # `{ "results": [] }`
            self.lastKnownError = "unknown PurpleAir sensorId"
            log.error(self.lastKnownError)
            return None

        try:
            timestamp = result["LastSeen"]  # unix timestamp
            temp_f = float(result["temp_f"])
            humidity = float(result["humidity"])  # 0..100
            pressure_millibars = float(result["pressure"])
        except (KeyError, TypeError, ValueError) as err:
            self.lastKnownError = "unexpected response format"
            log.exception(self.lastKnownError, exc_info=err)
            return None

        # Filter out responses that are too old (e.g., offline sensors).
        # (Another approach would be to check result["AGE"], which is in minutes.)
        data_age_minutes = (time.time() - timestamp) / 60
        if data_age_minutes > self.maxAgeMinutes:
            self.lastKnownError = "ignoring old data (%d minutes)" % data_age_minutes
            log.warning(self.lastKnownError)
            return None

        # Device internal temp_f is 8 degrees higher than ambient temperature
        # (per https://www2.purpleair.com/community/faq#!hc-primary-and-secondary-data-header)
        temp_f = temp_f - 8.0

        # Convert from PurpleAir's to RainMachine's preferred units
        temp_c = (temp_f - 32.0) * 5.0 / 9.0
        pressure_kpa = pressure_millibars / 10.0  # PurpleAir reports millibars

        return {
            "timestamp": timestamp,
            RMParser.dataType.TEMPERATURE: temp_c,
            RMParser.dataType.RH: humidity,
            RMParser.dataType.PRESSURE: pressure_kpa,
        }

    def add_sensor_data(self, cleaned):
        timestamp = cleaned.pop("timestamp")
        for data_type, value in cleaned.items():
            self.addValue(data_type, timestamp, value)
            log.debug("added '%s': %0.1f at %d" % (data_type, value, timestamp))
