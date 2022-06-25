from os import environ
from textwrap import dedent
from unittest import TestCase

from mock import ANY, MagicMock, patch

from .rm_log_utils import clear_log, get_log
from .utils import Approximately

from purpleair_parser import PurpleAir


class ParserBaseTestCase(TestCase):
    def setUp(self):
        super(ParserBaseTestCase, self).setUp()

        # mock RMParser.addValue
        add_value_patcher = patch.object(PurpleAir, "addValue")
        self.addCleanup(add_value_patcher.stop)
        self.mock_add_value = add_value_patcher.start()

    def run_parser(self, **params):
        clear_log()
        parser = PurpleAir()
        parser.params.update(params)
        parser.perform()
        self.parser_log = get_log()
        return parser


class MockPurpleAirAPITests(ParserBaseTestCase):
    """Mock the PurpleAir API using response fixtures"""

    def setUp(self):
        super(MockPurpleAirAPITests, self).setUp()

        # mock RMParser.openURL
        open_url_patcher = patch.object(PurpleAir, "openURL")
        self.addCleanup(open_url_patcher.stop)
        self.mock_open_url = open_url_patcher.start()

        # test data was generated shortly before timestamp 1656112000
        time_patcher = patch("time.time", return_value=1656112000)
        self.addCleanup(time_patcher.stop)
        self.mock_time = time_patcher.start()

    def set_open_url_response(self, body, status_code=200):
        body = dedent(body)
        if status_code < 400:
            mock_response = MagicMock(read=MagicMock(return_value=body))
            self.mock_open_url.return_value = mock_response
        else:
            # RMParser.openURL traps all urllib2.urlopen errors, logs them, and returns None
            self.mock_open_url.return_value = None
            # To test the actual error, mock urllib2.urlopen instead of Parser.openURL...
            # error = urllib2.HTTPError(url, status_code, "", [], StringIO(body))
            # patch("RMParserFramework.rmParser.urllib2.urlopen", side_effect=error)

    def test_normal_operation(self):
        self.set_open_url_response("""\
            {
                "api_version" : "V1.0.10-0.0.17",
                "time_stamp" : 1656110602,
                "data_time_stamp" : 1656110554,
                "sensor" : {
                    "sensor_index" : 70735,
                    "name" : "Rhode Island and 18th",
                    "last_seen" : 1656110471,
                    "humidity" : 35,
                    "temperature" : 81,
                    "pressure" : 1008.0
                }
            }""")
        parser = self.run_parser(apiKey="TEST_KEY", sensorId=70735, keyForPrivateSensor="")

        self.mock_open_url.assert_called_once_with(
            "https://api.purpleair.com/v1/sensors/70735",
            {"fields": "sensor_index,name,last_seen,humidity,temperature,pressure"},
            headers={"user-agent": ANY, "X-API-Key": "TEST_KEY"})

        self.mock_add_value.assert_any_call("RH", 1656110471, Approximately(45.618, places=3))
        self.mock_add_value.assert_any_call("PRESSURE", 1656110471, Approximately(100.8))
        self.mock_add_value.assert_any_call("TEMPERATURE", 1656110471, Approximately(22.778, places=3))
        self.assertEqual(self.mock_add_value.call_count, 3)

        self.assertEqual(parser.lastKnownError, "")

    def test_private_sensor(self):
        self.set_open_url_response("""\
            {
                "api_version" : "V1.0.10-0.0.17",
                "time_stamp" : 1656110602,
                "data_time_stamp" : 1656110554,
                "sensor" : {
                    "sensor_index" : 70735,
                    "name" : "Rhode Island and 18th",
                    "last_seen" : 1656110471,
                    "humidity" : 35,
                    "temperature" : 81,
                    "pressure" : 1008.0
                }
            }""")
        self.run_parser(apiKey="TEST_KEY", sensorId="70735", keyForPrivateSensor="ABCDEFG")
        self.mock_open_url.assert_called_once_with(
            "https://api.purpleair.com/v1/sensors/70735",
            {"read_key": "ABCDEFG", "fields": ANY},
            headers={"user-agent": ANY, "X-API-Key": "TEST_KEY"})

    def test_offline(self):
        # This sensor has been offline for more than one hour, so should be ignored
        self.set_open_url_response("""\
            {
                "api_version" : "V1.0.10-0.0.17",
                "time_stamp" : 1656110869,
                "data_time_stamp" : 1656110858,
                "sensor" : {
                    "sensor_index" : 3666,
                    "name" : "Isis St",
                    "last_seen" : 1656107176,
                    "humidity" : 44,
                    "temperature" : 79,
                    "pressure" : 1012.5
                }
            }""")
        parser = self.run_parser(apiKey="TEST_KEY", sensorId="3666")
        self.assertEqual(parser.lastKnownError, "ignoring old data (80 minutes)")
        self.mock_add_value.assert_not_called()

    def test_unregistered_sensor_id(self):
        self.set_open_url_response("""\
            {
                "api_version": "V1.0.10-0.0.17",
                "time_stamp": 1656110967,
                "error": "NotFoundError",
                "description": "Cannot find a sensor with the provided parameters."
            }""", status_code=404)
        parser = self.run_parser(apiKey="TEST_KEY", sensorId="2")
        self.assertEqual(parser.lastKnownError, "error querying PurpleAir sensor '2'; check logs")
        self.mock_add_value.assert_not_called()

    def test_invalid_sensor_id(self):
        self.set_open_url_response("""\
            {
                "api_version": "V1.0.10-0.0.17",
                "time_stamp": 1656111193,
                "error": "InvalidParameterValueError",
                "description": "The value provided for parameter 'sensor_index' was not valid."
            }""", status_code=400)
        parser = self.run_parser(apiKey="TEST_KEY", sensorId="~/?foo=1#bar")
        # Make sure sensorId is properly escaped for url:
        self.mock_open_url.assert_called_once_with(
            "https://api.purpleair.com/v1/sensors/%7E%2F%3Ffoo%3D1%23bar",
            {"fields": ANY}, headers=ANY)
        self.assertEqual(parser.lastKnownError,
                         "error querying PurpleAir sensor '~/?foo=1#bar'; check logs")
        self.mock_add_value.assert_not_called()

    def test_invalid_api_key(self):
        self.set_open_url_response("""\
            {
                "api_version": "V1.0.10-0.0.17",
                "time_stamp": 1656117000,
                "error": "ApiKeyInvalidError",
                "description": "The provided api_key was not valid."
            }""", status_code=403)
        parser = self.run_parser(apiKey="INVALID_KEY", sensorId="70735")
        self.assertEqual(parser.lastKnownError, "error querying PurpleAir sensor '70735'; check logs")
        self.mock_add_value.assert_not_called()

    def test_api_key_required(self):
        parser = self.run_parser(apiKey="", sensorId="123")
        self.assertEqual(parser.lastKnownError, "must set PurpleAir apiKey")
        self.mock_add_value.assert_not_called()

    def test_sensor_id_required(self):
        parser = self.run_parser(apiKey="foo", sensorId="")
        self.assertEqual(parser.lastKnownError, "must set PurpleAir sensorId")
        self.mock_add_value.assert_not_called()


class LiveIntegrationTests(ParserBaseTestCase):
    """Call the live PurpleAir API"""

    def test_live_purpleair_sensor(self):
        # Set environment TEST_PURPLEAIR_API_KEY to your READ API key (required),
        # and optionally TEST_PURPLEAIR_SENSOR_ID to test with your sensor id
        live_api_key = environ.get("TEST_PURPLEAIR_API_KEY")
        if not live_api_key:
            self.skipTest("TEST_PURPLEAIR_API_KEY must be set to run live tests")
        live_sensor_id = environ.get("TEST_PURPLEAIR_SENSOR_ID", "70735")
        parser = self.run_parser(apiKey=live_api_key, sensorId=live_sensor_id)

        self.mock_add_value.assert_any_call("RH", ANY, ANY)
        self.mock_add_value.assert_any_call("PRESSURE", ANY, ANY)
        self.mock_add_value.assert_any_call("TEMPERATURE", ANY, ANY)
        self.assertEqual(self.mock_add_value.call_count, 3)

        self.assertEqual(parser.lastKnownError, "")
