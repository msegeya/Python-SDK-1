# -*- coding: utf-8 -*-
import time
import unittest
from datetime import datetime, timedelta

from knurld_sdk.APIManager import TokenGetter, AppModel, Consumer, Enrollment, Analysis, Verification
from knurld_sdk import helpers as h


def temp_token():
    # obtain a valid admin token
    tg = TokenGetter()
    return tg.get_token()


class TestVerification(unittest.TestCase):
    test_model_id = '5571c3a5c203f17826740e901903cafb'  # "boston", "chicago", "pyramid"
    test_consumer_id = '3c1bbea5f380bcbfef6910e0c879bf82'  # M theo walcott
    e = Enrollment(temp_token(), app_model_id=test_model_id, consumer_id=test_consumer_id)
    v = Verification(temp_token(), app_model_id=test_model_id, consumer_id=test_consumer_id)

    def test_create(self):
        p = {
            "enrollment.wav": h.DummyData.enrollment_wav,
            "intervals": h.DummyData.intervals,
        }

        # test_enrollment_id = self.e.steps(payload_update=p)
        # print('Enrollment: ' + str(test_enrollment_id))

        # for i in range(5):
        #    time.sleep(0.5)
        #    response = self.e.get(test_enrollment_id)
        #    print('Enrollment Status: ' + str(response))

        verification_id = self.v.create()
        print('Verification: ' + str(verification_id))

        self.assertRegexpMatches(verification_id, h.regx_pattern_id())


class TestEnrollment(unittest.TestCase):
    test_model_id = '5571c3a5c203f17826740e901903cafb'  # "boston", "chicago", "pyramid"
    test_consumer_id = '3c1bbea5f380bcbfef6910e0c879bf82'  # M theo walcott
    e = Enrollment(temp_token(), app_model_id=test_model_id, consumer_id=test_consumer_id)

    def test_create(self):
        enrollment_id = self.e.create()
        print(enrollment_id)
        self.assertRegexpMatches(enrollment_id, h.regx_pattern_id())

    def test_update(self):
        test_enrollment_id = self.e.create()
        # a valid payload test
        p = {
            "enrollment.wav": h.DummyData.enrollment_wav,
            "intervals": h.DummyData.intervals,
        }
        enrollment_id = self.e.update(test_enrollment_id, payload_update=p)
        self.assertRegexpMatches(enrollment_id, h.regx_pattern_id())

        # an invalid payload test
        p = {
            "enrollment.wav": h.DummyData.invalid_enrollment_wav,
            "intervals": h.DummyData.incorrect_intervals,
        }
        status, response = self.e.update(test_enrollment_id, payload_update=p)
        self.assertEqual(status, 400)
        self.assertIsNotNone(response)

    def test_get(self):
        test_enrollment_id = self.e.create()
        response = self.e.get(test_enrollment_id)
        self.assertIsNotNone(response.get('href'))
        self.assertIsNotNone(response.get('instructions'))

    def test_get_all(self):
        response = self.e.get_all()
        self.assertIsNotNone(response.get('items'))

    def test_steps(self):
        p = {
            "enrollment.wav": h.DummyData.enrollment_wav,
            "intervals": h.DummyData.intervals,
        }
        enrollment_id = self.e.steps(payload_update=p)
        self.assertRegexpMatches(enrollment_id, h.regx_pattern_id())


class TestAnalysis(unittest.TestCase):

    ap = {
        "vocabulary": ["boston", "chicago", "pyramid"],
        "verificationLength": 3,
        "enrollmentRepeats": 3
    }
    test_app_model = AppModel(temp_token(), payload=ap)

    cp = {
        # a unique username for testing
        "username": 'theo_' + str(datetime.now()),
        "password": 'walcott',
        "gender": 'M'
    }
    test_consumer = Consumer(token=temp_token(), payload=cp)

    p = {
        "audioUrl": h.DummyData.enrollment_wav,
        "words": 3
    }
    a = Analysis(temp_token(), app_model_id=test_app_model, consumer_id=test_consumer, payload=p)

    def test_start_task(self):
        task = self.a.start_task()
        self.assertIsNotNone(task)
        self.assertEqual(task.get('taskStatus'), 'started')
        self.assertRegexpMatches(task.get('taskName'), h.regx_pattern_id())

    def test_check_status(self):
        task = self.a.start_task()
        self.assertIsNotNone(task)
        test_task_name = task.get('taskName')
        result = self.a.check_status(test_task_name)

        self.assertIn(result.get('taskStatus'), ['running', 'completed'])
        if result.get('taskStatus') == 'completed':
            self.assertIsNotNone(result.get('intervals'))
            print(result.get('intervals'))

    def test_steps(self):
        result = self.a.steps()
        self.assertIsNotNone(result)
        self.assertEqual(result.get('taskStatus'), 'completed')
        self.assertIsNotNone(result.get('intervals'))

    def test_intervals_with_phrases(self):
        result = self.a.steps()
        intervals = result.get('intervals')
        modified_intervals = h.merge_intervals_with_phrases(self.ap.get('vocabulary'),
                                                            self.ap.get('enrollmentRepeats'),
                                                            intervals)
        self.assertIsNotNone(modified_intervals)


class TestConsumer(unittest.TestCase):

    p = {
        # a unique username for testing
        "username": 'theo_' + str(datetime.now()),
        "password": 'walcott',
        "gender": 'M'
    }
    c = Consumer(token=temp_token(), payload=p)

    def test_create(self):
        consumer = self.c.create()
        self.assertRegexpMatches(consumer, h.regx_pattern_id())

    def test_update(self):
        p = {
            # a unique username for testing
            "username": 'theo_' + str(datetime.now()) + '_alias',
            "password": 'walcott',
            "gender": 'M'
        }
        c_alias = Consumer(token=temp_token(), payload=p)
        test_consumer_id = c_alias.create()
        p = {
            "password": 'walcott360'
        }
        consumer = c_alias.update(test_consumer_id, payload_override=p)
        self.assertRegexpMatches(consumer, h.regx_pattern_id())

    def test_get(self):
        p = {
            # a unique username for testing
            "username": 'theo_' + str(datetime.now()) + '_alias',
            "password": 'walcott',
            "gender": 'M'
        }
        c_alias = Consumer(token=temp_token(), payload=p)
        test_consumer_id = c_alias.create()
        result = c_alias.get(test_consumer_id)
        self.assertIsNotNone(result.get('href'))

    def test_get_all(self):
        result = self.c.get_all()
        self.assertIsNotNone(result.get('items'))

    def delete(self):
        pass


class TestAppModel(unittest.TestCase):
    p = {
        "vocabulary": ["boston", "chicago", "pyramid"],
        "verificationLength": 3,
        "enrollmentRepeats": 3
    }
    am = AppModel(temp_token(), payload=p)
    test_app_model_id = am.create()

    def test_bad_payload(self):
        payload = {
            "vocabulary": ["boston", "chicago", "pyramid"],
            "enrollmentRepeats": 3
        }
        self.assertIsNone(self.am.set_payload(payload))

    def test_good_payload(self):
        payload = {
            "vocabulary": ["boston", "chicago", "pyramid"],
            "verificationLength": 3,
            "enrollmentRepeats": 3
        }
        self.assertIsNotNone(self.am.set_payload(payload))

    def test_create(self):
        self.assertRegexpMatches(self.test_app_model_id, h.regx_pattern_id())

    def test_update(self):
        self.assertRegexpMatches(self.test_app_model_id, h.regx_pattern_id())

        payload = {
            "enrollmentRepeats": 3,
            "threshold": 0,
            "autoThresholdEnable": False,
            "autoThresholdClearance": 0,
            "autoThresholdMaxRise": 0,
            "useModelUpdate": False,
            "modelUpdateDailyLimit": 0
        }
        app_model_id = self.am.update(app_model_id=self.test_app_model_id, payload_override=payload)
        self.assertRegexpMatches(app_model_id, h.regx_pattern_id())

    def test_get(self):
        result = self.am.get(self.test_app_model_id)
        self.assertIsNotNone(result.get('href'))

        # read only app model
        test_model_id = '5571c3a5c203f17826740e901903cafb'  # "boston", "chicago", "pyramid"
        ro_am = AppModel(temp_token(), payload=None)
        ro_am.get(test_model_id)

    def test_get_all(self):
        result = self.am.get_all()
        self.assertIsNotNone(result.get('href'))

    def delete(self):
        pass


class TestTokenGetter(unittest.TestCase):

    tg = TokenGetter()

    def test_renew_access_token(self):

        # new token must be the one just got fetched using remote APIs
        token = self.tg.renew_access_token()
        self.assertEqual(self.tg._token, token)

    def test_is_valid_token(self):

        # set up for an unexpired token (assuming self.tg object is created just a moments ago, this is a valid token)
        self.tg.renew_access_token()
        is_valid = self.tg._is_valid_token(self.tg._token)
        self.assertEqual(True, is_valid)

        # set up for an expired token
        self.tg._token_timestamp = datetime.now() - timedelta(seconds=3600)

        # the current token may or may not be valid based on the tg timestamp
        is_valid = self.tg._is_valid_token(self.tg._token)
        self.assertEqual(False, is_valid)

    def test_get_token(self):
        # set up for an expired token
        cur_token = self.tg._token
        new_token = self.tg.get_token()
        self.assertNotEqual(cur_token, new_token)

        # set up for an unexpired token (assuming self.tg object is created just a moments ago, this is a valid token)
        self.assertEqual(new_token, self.tg.get_token())

    def token_renew_frequency(self):
        """
        With this test, a token is set to expire every 10 seconds
        Fetches and prints a token at 2 seconds interval
        Assert that we get two unique tokens
        TODO: This is actually a functional test which needs to be placed at more appropriate location
        """
        until = 10
        interval = 2

        # get the token that expires in 10 seconds
        self.tg = TokenGetter(expires=10)

        tokens = []
        # check if the token expires properly in set interval and the new toke is successfully fetched after expiry only
        for i in range(1, until):
            time.sleep(interval)

            # fetch token
            token = self.tg.get_token()
            print('TOKEN: ---> ' + str(token))

            # put it in the list
            tokens.append(token)

        # assert for exactly two unique tokens during 10 * 2 = 20 seconds of overall time
        self.assertEquals(len(set(tokens)), 2)


if __name__ == '__main__':
    unittest.main()
