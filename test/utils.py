import os.path


class Approximately(float):
    """Matcher for approximate number comparison.

    Usage:
        mock_object.assert_called_with(AlmostEqual(0.3))
        mock_object.assert_called_with(AlmostEqual(0.667, places=3))
    """

    def __new__(cls, value, places=7):
        self = super(Approximately, cls).__new__(cls, value)
        self.places = places
        return self

    def __eq__(self, other):
        return round(abs(other - self), self.places) == 0


FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "__fixtures__")


def load_fixture(fixture_name):
    with open(os.path.join(FIXTURES_DIR, fixture_name)) as f:
        return f.read()
