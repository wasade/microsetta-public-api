import functools
import json
import types
import tempfile
from unittest.case import TestCase
from unittest.mock import patch

import microsetta_public_api
import microsetta_public_api.server
import microsetta_public_api.utils._utils
from microsetta_public_api import config
from microsetta_public_api.resources import resources


class TempfileTestCase(TestCase):

    def setUp(self):
        self._tempfiles = []

    def create_tempfile(self, **named_temporary_file_kwargs):
        # See the docs here for kwargs:
        # https://docs.python.org/3/library/tempfile.html
        new_tempfile = tempfile.NamedTemporaryFile(
            **named_temporary_file_kwargs)
        self._tempfiles = []
        return new_tempfile

    def tearDown(self):
        for tempfile_ in self._tempfiles:
            tempfile_.close()


class FlaskTests(TestCase):

    def setUp(self):

        self.app, self.client = self.build_app_test_client()
        self.app_context = self.app.app.app_context

    @staticmethod
    def build_app_test_client():
        app = microsetta_public_api.server.build_app()
        client = app.app.test_client()
        return app, client

    def assertStatusCode(self, exp_code, response):
        try:
            status_code = response.status_code
            self.assertEqual(exp_code, status_code)
        except AssertionError:
            raise AssertionError(f'{exp_code} != {status_code}'
                                 f'\nRecieved response data: {response.data}')


def _copy_func(f, name=None):
    """
    Based on https://stackoverflow.com/q/13503079
    """
    g = types.FunctionType(f.__code__, f.__globals__, name or f.__name__,
                           argdefs=f.__defaults__, closure=f.__closure__)
    g = functools.update_wrapper(g, f)
    g.__kwdefaults__ = f.__kwdefaults__
    return g


class MockedResponse(str):

    def __init__(self, data):
        super().__init__()
        self.data = data

    def __eq__(self, other):
        if isinstance(other, MockedResponse):
            return self.data == other.data
        else:
            return self.data == other


def mocked_jsonify(*args, **kwargs):
    """Can be used to replace flask.jsonify, since it does not work
    outside of a application context

    From the flask docs:
        1. Single argument: Passed straight through to dumps
        2. Multiple arguments: converted to array and passed to dumps
        3. Multiple kwargs: converted to a dict and passed to dumps
        4. Both args and kwargs: behavior undefined and will throw an exception

    Additionally, a _MockedWebResponse object the
    """
    # need to return an object so its attributes can be set (like in get_alpha)
    def dump(data):
        return MockedResponse(json.dumps(data))
    if len(args) == 1 and len(kwargs) == 0:
        return dump(*args)
    elif len(args) > 1 and len(kwargs) == 0:
        return dump([arg for arg in args])
    elif len(args) == 0 and len(kwargs) > 0:
        return dump(kwargs)
    else:
        raise TypeError(f"mocked_jsonify got an unexpected combination of "
                        f"args and kwargs. Got args={args}, kwargs={kwargs}.")


class MockedJsonifyTestCase(TestCase):

    def setUp(self):
        if isinstance(self.jsonify_to_patch, str):
            self.jsonify_patcher = patch(
                self.jsonify_to_patch,
                new=mocked_jsonify,
            )
            self.mock_jsonify = self.jsonify_patcher.start()
        else:
            self.jsonify_patcher = [patch(jsonify_, new=mocked_jsonify) for
                                    jsonify_ in self.jsonify_to_patch]
            self.mock_jsonify = [patcher.start() for
                                 patcher in self.jsonify_patcher]

    def tearDown(self):
        if isinstance(self.mock_jsonify, list):
            for patcher in self.jsonify_patcher:
                patcher.stop()
        else:
            self.jsonify_patcher.stop()


class ConfigTestCase(TestCase):

    def setUp(self):
        self._config_copy = config.resources.copy()
        self._resources_copy = resources.copy()

    def tearDown(self):
        config.resources = self._config_copy
        resources.clear()
        dict.update(resources, self._resources_copy)
