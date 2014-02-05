import unittest

import mock
import uuid
import struct
from nsq import response
from nsq import constants
from nsq import exceptions


class TestResponse(unittest.TestCase):
    '''Test our response class'''
    def test_from_raw_response(self):
        '''Make sure we can construct a raw response'''
        raw = struct.pack('>l5s', constants.FRAME_TYPE_RESPONSE, 'hello')
        res = response.Response.from_raw(None, raw)
        self.assertEqual(res.__class__, response.Response)
        self.assertEqual(res.data, 'hello')

    def test_from_raw_unknown_frame(self):
        '''Raises an exception for unknown frame types'''
        raw = struct.pack('>l5s', 9042, 'hello')
        self.assertRaises(TypeError, response.Response.from_raw, None, raw)

    def test_str(self):
        '''Has a reasonable string value'''
        raw = struct.pack('>l5s', constants.FRAME_TYPE_RESPONSE, 'hello')
        res = response.Response.from_raw(None, raw)
        self.assertEqual(str(res), 'Response - hello')


class TestError(unittest.TestCase):
    '''Test our error response class'''
    def test_from_raw_error(self):
        '''Can identify an error type'''
        raw = struct.pack('>l5s', constants.FRAME_TYPE_ERROR, 'hello')
        res = response.Response.from_raw(None, raw)
        self.assertEqual(res.__class__, response.Error)
        self.assertEqual(res.data, 'hello')

    def test_str(self):
        '''Has a reasonable string value'''
        raw = struct.pack('>l5s', constants.FRAME_TYPE_ERROR, 'hello')
        res = response.Response.from_raw(None, raw)
        self.assertEqual(str(res), 'Error - hello')

    def test_find(self):
        '''Can correctly identify the appropriate exception'''
        expected = {
            'E_INVALID': exceptions.InvalidException,
            'E_BAD_BODY': exceptions.BadBodyException,
            'E_BAD_TOPIC': exceptions.BadTopicException,
            'E_BAD_CHANNEL': exceptions.BadChannelException,
            'E_BAD_MESSAGE': exceptions.BadMessageException,
            'E_PUB_FAILED': exceptions.PubFailedException,
            'E_MPUB_FAILED': exceptions.MpubFailedException,
            'E_FIN_FAILED': exceptions.FinFailedException,
            'E_REQ_FAILED': exceptions.ReqFailedException,
            'E_TOUCH_FAILED': exceptions.TouchFailedException
        }
        for key, klass in expected.items():
            self.assertEqual(response.Error.find(key), klass)

    def test_find_missing(self):
        '''Raises an exception if it can't find the appropriate exception'''
        self.assertRaises(TypeError, response.Error.find, 'woruowijklf')

    def test_exception(self):
        '''Can correctly raise the appropriate exception'''
        raw = struct.pack('>l13s', constants.FRAME_TYPE_ERROR, 'E_INVALID foo')
        res = response.Response.from_raw(None, raw)
        exc = res.exception()
        self.assertIsInstance(exc, exceptions.InvalidException)
        self.assertEqual(exc.message, 'foo')


class TestMessage(unittest.TestCase):
    '''Test our message case'''
    def setUp(self):
        self.id = uuid.uuid4().hex[:16]
        self.timestamp = 0
        self.attempt = 1
        self.body = 'hello'
        self.packed = struct.pack('>qH16s5s', 0, 1, self.id, self.body)
        self.response = response.Response.from_raw(mock.Mock(),
            struct.pack('>l31s', constants.FRAME_TYPE_MESSAGE, self.packed))

    def test_str(self):
        '''Has a reasonable string value'''
        self.assertEqual(str(self.response), 'Message - 0 1 %s hello' % self.id)

    def test_from_raw_message(self):
        '''Can identify a message type'''
        self.assertEqual(self.response.__class__, response.Message)

    def test_timestamp(self):
        '''Can identify the timestamp'''
        self.assertEqual(self.response.timestamp, self.timestamp)

    def test_attempts(self):
        '''Can identify the number of attempts'''
        self.assertEqual(self.response.attempts, self.attempt)

    def test_id(self):
        '''Can identify the ID of the message'''
        self.assertEqual(self.response.id, self.id)

    def test_message(self):
        '''Can properly detect the message'''
        self.assertEqual(self.response.body, self.body)

    def test_fin(self):
        '''Invokes the fin method'''
        self.response.fin()
        self.response.connection.fin.assert_called_with(self.id)

    def test_req(self):
        '''Invokes the req method'''
        self.response.req(1)
        self.response.connection.req.assert_called_with(self.id, 1)

    def test_touch(self):
        '''Invokes the touch method'''
        self.response.touch()
        self.response.connection.touch.assert_called_with(self.id)