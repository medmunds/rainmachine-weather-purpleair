from os import environ
from StringIO import StringIO
from unittest import TestCase
from urllib2 import HTTPError

from mock import ANY, MagicMock, patch

from .rm_log_utils import clear_log, get_log
from .utils import Approximately, load_fixture

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

        # most fixtures were generated shortly before timestamp 1627065300
        time_patcher = patch("time.time", return_value=1627065300)
        self.addCleanup(time_patcher.stop)
        self.mock_time = time_patcher.start()

    def set_open_url_response(self, fixture_name):
        body = load_fixture(fixture_name)
        mock_response = MagicMock(read=MagicMock(return_value=body))
        self.mock_open_url.return_value = mock_response

    def set_open_url_error(self, error):
        # openURL traps all urllib2.urlopen errors, logs them, and returns None
        self.mock_open_url.return_value = None

        # To test the actual error, mock urllib2.urlopen instead of Parser.openURL...
        # patch("RMParserFramework.rmParser.urllib2.urlopen", side_effect=error)

    def test_normal_operation(self):
        self.set_open_url_response("purpleair-outdoor.json")
        parser = self.run_parser(sensorId="70735", keyForPrivateSensor="")

        self.mock_open_url.assert_called_once_with(
            "https://www.purpleair.com/json", {"show": "70735"},
            headers={"user-agent": ANY})

        self.mock_add_value.assert_any_call("RH", 1627065227, Approximately(50.0))
        self.mock_add_value.assert_any_call("PRESSURE", 1627065227, Approximately(101.359))
        self.mock_add_value.assert_any_call("TEMPERATURE", 1627065227, Approximately(16.667, places=3))
        self.assertEqual(self.mock_add_value.call_count, 3)

        self.assertEqual(parser.lastKnownError, "")

    def test_private_sensor(self):
        self.set_open_url_response("purpleair-outdoor.json")
        self.run_parser(sensorId="70735", keyForPrivateSensor="ABCDEFG")
        self.mock_open_url.assert_called_once_with(
            "https://www.purpleair.com/json", {"show": "70735", "key": "ABCDEFG"},
            headers={"user-agent": ANY})

    def test_offline(self):
        # This sensor has been offline for more than one hour, so should be ignored
        self.set_open_url_response("purpleair-offline.json")
        parser = self.run_parser(sensorId="85803")
        self.assertEqual(parser.lastKnownError, "ignoring old data (11193 minutes)")
        self.mock_add_value.assert_not_called()

    def test_unregistered_sensor_id(self):
        self.set_open_url_response("purpleair-unregistered-sensor-id.json")
        parser = self.run_parser(sensorId="2")
        self.assertEqual(parser.lastKnownError, "unknown PurpleAir sensorId")
        self.mock_add_value.assert_not_called()

    def test_invalid_sensor_id(self):
        body = load_fixture("purpleair-invalid-sensor-id.json")
        error = HTTPError("https://www.purpleair.com/json?show=ABC", 400, "INVALID", [], StringIO(body))
        self.set_open_url_error(error)

        parser = self.run_parser(sensorId="ABC")
        self.assertEqual(parser.lastKnownError, "error querying PurpleAir sensor 'ABC'; check logs")
        self.mock_add_value.assert_not_called()

    def test_sensor_id_required(self):
        parser = self.run_parser(sensorId="")
        self.assertEqual(parser.lastKnownError, "must set PurpleAir sensorId")
        self.mock_add_value.assert_not_called()


class LiveIntegrationTests(ParserBaseTestCase):
    """Call the live PurpleAir API"""

    def test_live_purpleair_sensor(self):
        # Set environment TEST_PURPLEAIR_SENSOR_ID to test with your sensor id
        live_sensor_id = environ.get("TEST_PURPLEAIR_SENSOR_ID", "70735")
        parser = self.run_parser(sensorId=live_sensor_id)

        self.mock_add_value.assert_any_call("RH", ANY, ANY)
        self.mock_add_value.assert_any_call("PRESSURE", ANY, ANY)
        self.mock_add_value.assert_any_call("TEMPERATURE", ANY, ANY)
        self.assertEqual(self.mock_add_value.call_count, 3)

        self.assertEqual(parser.lastKnownError, "")
