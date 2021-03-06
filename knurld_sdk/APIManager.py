# -*- coding: utf-8 -*-
"""
# Copyright 2016 Intellisis Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file
"""

import json
import re
import requests
import time
from datetime import datetime

from knurld_sdk import app_globals as g
from knurld_sdk import helpers as h
from knurld_sdk.CustomExceptions import ImproperArgumentsException


def authorization_header(token=None, content_type='application/json', developer_id=None):

    try:
        tg = TokenGetter()
        token = token if token else tg.get_token()

        headers = {
            'Content-Type': content_type,
            'Authorization': 'Bearer ' + str(token),
            'Developer-Id': g.config['DEVELOPER_ID']
        }
        # for a consumer the consumer token replaces the Developer-Id
        if developer_id:
            headers['Developer-Id'] = developer_id

        return headers

    except Exception as e:
        print('Could not obtain Authorization header' + str(e))
        return None


class Verification(object):

    # can leave app_model_id & consumer_id blank, for readonly objects
    def __init__(self, token, app_model_id='', consumer_id=''):
        self.token = token
        self.app_model_id = app_model_id
        self.consumer_id = consumer_id
        self.verification_url = None

    @property
    def verification_id(self):
        return h.parse_id_from_href(self.verification_url)

    @property
    def payload(self):
        p = {
            "consumer": self.consumer_id,
            "application": self.app_model_id
        }
        return p

    def create(self):
        """ create or register the verification work order
        """
        headers = authorization_header()

        try:
            url = g.config['URL_VERIFICATIONS']
            response = requests.post(url, json=self.payload, headers=headers)
            print(response)
            print(response.content)
            if response.status_code == 201:
                result = json.loads(response.content)
                self.verification_url = result.get('href')
                return self.verification_id
            else:
                return response.status_code, response.content
        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def update(self, verification_id, payload_update):
        """ update existing verification work order with a payload containing wav_file and/or intervals
        :param verification_id: existing verification id you receive upon create
        :param payload_update: e.g.
                {
                    "verification.wav": "",
                    "intervals": [
                        {
                            "phrase": "",
                            "start": 0,
                            "stop": 0
                        },
                        { .... }
                    ]
                }
        """
        # TODO: could change this to use the consumer specific tokens in the future, with developer_id param to headers
        headers = authorization_header()

        try:
            url = g.config['URL_VERIFICATIONS'] + '/' + verification_id
            response = requests.post(url, json=payload_update, headers=headers)
            print(response)
            print(response.content)
            if response.status_code == 202:
                result = json.loads(response.content)
                self.verification_url = result.get('href')
                return self.verification_id
            else:
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def get(self, verification_id):
        """ get verification for the given enrollment id
        """
        headers = authorization_header()

        try:
            url = g.config['URL_VERIFICATIONS'] + '/' + verification_id

            response = requests.get(url, headers=headers)
            print(response)
            print(response.content)

            if response.status_code == 200:
                result = json.loads(response.content)
                self.verification_url = result.get('href')
                return result
            else:
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    @staticmethod
    def get_all(limit=10, offset=0):
        """ return all the verifications for given offset, start, end
            TODO: the proper usage of parameters when pagination is needed
        """
        headers = authorization_header()

        try:
            url = g.config['URL_VERIFICATIONS'] + '?limit=' + str(limit) + '&offset=' + str(offset)

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
                return result
            else:
                # TODO: log errors
                print(response.status_code)
                print(response.content)
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def step_one(self):
        """ create verification and get instructions
        """
        # create a fresh work order for verification, here self.verification_id is set internally
        verification_id = self.create()
        print('step-1: create: put verification_id, model_id: self.enrollment_id ' + str(self.verification_id))
        if not verification_id:
            return None

        # get the instructions for as to how to proceed with the verification
        instructions = self.get(self.verification_id)
        print('Follow these instructions to do proper Verification: ' + str(instructions.get('instructions')))
        if not instructions or type(instructions) == 'tuple':
            return None

        return instructions.get('instructions')

    def step_two(self, payload_update):
        """ using the instructions from step one developer must create the appropriate payload and pass it to step_two
        :param payload_update: e.g.
            payload = {
            "verification.wav": '',
            "intervals": [
                    {
                    "phrase": "",
                    "start": 0,
                    "stop": 0
                    },
                    { .... }
                ]
            }
        """
        # update the verification work order with the verification.wav and intervals payload
        status_time_lapse = 0
        status_timestamp = datetime.now()
        _ = self.update(self.verification_id, payload_update=payload_update)

        verify_result = None
        try:
            verify_result = self.get(self.verification_id)
            verify_status = verify_result.get('status')
            while unicode(verify_status) != u'completed' \
                    and status_time_lapse < float(g.config['REATTEMPT_CALLS_FOR']):
                time.sleep(0.01)
                verify_result = self.get(self.verification_id)
                verify_status = verify_result.get('status')
                print('* verification status: ' + str(verify_status))
                status_time_lapse = (datetime.now() - status_timestamp).total_seconds()

        except AttributeError as e:
            print('Verification check status error {}'.format(e))

        # finally, when the verification status is 'completed' return verification result
        print('Final result of Verification: ' + str(verify_result))
        return verify_result

    def delete(self, verification_id):
        """ delete verification with given id
        :param verification_id:
        :return: result of deletion
        """
        headers = authorization_header()

        try:
            url = g.config['URL_VERIFICATIONS'] + '/' + verification_id

            response = requests.delete(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
                if result.get('href'):
                    self.verification_url = result.get('href')
            else:
                # TODO: log errors
                print(response.status_code)
                print(response.content)
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

        return result


class Enrollment(object):

    # can leave app_model_id & consumer_id blank, for readonly objects
    def __init__(self, token, app_model_id='', consumer_id=''):
        self.token = token
        self.app_model_id = app_model_id
        self.consumer_id = consumer_id
        self.enrollment_url = None

    @property
    def enrollment_id(self):
        return h.parse_id_from_href(self.enrollment_url)

    @property
    def payload(self):
        p = {
            "application": self.app_model_id,
            "consumer": self.consumer_id
        }
        return p

    def create(self):
        """ create the enrollment using an app-model and consumer
        """
        headers = authorization_header()

        try:
            url = g.config['URL_ENROLLMENTS']

            response = requests.post(url, json=self.payload, headers=headers)
            if response.status_code == 201:
                result = json.loads(response.content)
                self.enrollment_url = result.get('href')
                return self.enrollment_id
            else:
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def update(self, enrollment_id, payload_update):
        """ update existing enrollment work order with a payload containing wav_file and/or intervals
        :param enrollment_id: existing enrollment id you receive upon create
        :param: payload_update: e.g.
                {
                    "enrollment.wav": "",
                    "intervals": [
                        {
                            "phrase": "",
                            "start": 0,
                            "stop": 0
                        },
                        { .... }
                    ]
                }
        """
        # TODO: could change this to use the consumer specific tokens in the future, with developer_id param
        headers = authorization_header()

        try:
            url = g.config['URL_ENROLLMENTS'] + '/' + enrollment_id
            response = requests.post(url, json=payload_update, headers=headers)
            print(response)
            print(response.content)
            if response.status_code == 202:
                result = json.loads(response.content)
                self.enrollment_url = result.get('href')
                return self.enrollment_id
            else:
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def get(self, enrollment_id):
        """ get enrollment for the given enrollment id
        """
        headers = authorization_header()

        try:
            url = g.config['URL_ENROLLMENTS'] + '/' + enrollment_id

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
                self.enrollment_url = result.get('href')
                return result
            else:
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    @staticmethod
    def get_all(limit=10, offset=0):
        """ return all the enrollments for given offset, start, end
            TODO: the proper usage of parameters when pagination is needed
        """
        headers = authorization_header()

        try:
            url = g.config['URL_ENROLLMENTS'] + '?limit=' + str(limit) + '&offset=' + str(offset)

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
                return result
            else:
                # TODO: log errors
                print(response.status_code)
                print(response.content)
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def steps(self, payload_update):

        # step-1: put consumer_id, model_id then the self.enrollment_id will be set automatically upon successful create
        enrollment_id = self.create()
        print('step-1: create: put consumer_id, model_id: self.enrollment_id ' + str(self.enrollment_id))
        if not enrollment_id:
            return None

        # step-2: get consumer token, to be used instead of the admin token in the header
        # consumer_token = self.consumer.get_token()
        # print('step-2: get consumer token: consumer_token: ' + str(consumer_token))

        # step-3: get enrollment instructions
        instructions = self.get(self.enrollment_id)
        print('Follow these instructions to do proper Enrollment: ' + str(instructions))
        if not instructions or type(instructions) == 'tuple':
            return None

        # step-4: record the .wav file - this should now be the part of the payload_update passed to this method
        # this step is independent of the other operations in this method
        # recorded_file_url = record_upload_share

        # step-5: get the endpoint analysis for the recorded .wav file
        # try:
        #    payload_update['audioUrl'] = payload_update.pop('enrollment.wav')
        # except KeyError as e:
        #    print("Your payload update must have 'enrollment.wav' key having a recorded file url as its value.")
        #    return None

        # a = Analysis(self.token, self.app_model_id, self.consumer_id, payload=payload_update)
        # task_name = a.start_task()
        # completed_task_name = a.check_status(task_name)
        # intervals = instructions.get('intervals')

        # build the intervals for enrollment

        # step-6: post the .wav file along with the intervals, complete enrollment

        status_time_lapse = 0
        status_timestamp = datetime.now()
        enrollment_id = self.update(self.enrollment_id, payload_update=payload_update)
        # make sure to send the enrollment id only after the status is changed to completed,
        # limited by config param REATTEMPT_CALLS_FOR

        try:
            enroll_status = self.get(self.enrollment_id).get('status')
            while unicode(enroll_status) not in [u'completed', u'failed']\
                    and status_time_lapse < float(g.config['REATTEMPT_CALLS_FOR']):

                time.sleep(0.01)
                enroll_status = self.get(self.enrollment_id).get('status')
                print('* enrollment status: ' + str(enroll_status))
                status_time_lapse = (datetime.now() - status_timestamp).total_seconds()

                if unicode(enroll_status) == u'failed':
                    return None

        except AttributeError as e:
            print('Enrollment check status error {}'.format(e))

        # returns the enrollment_id after the enrollment status becomes 'completed'
        return enrollment_id

    def delete(self, enrollment_id):
        """ delete enrollment with given id
        :param enrollment_id:
        :return: result of deletion
        """
        headers = authorization_header()

        try:
            url = g.config['URL_ENROLLMENTS'] + '/' + enrollment_id

            response = requests.delete(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
                if result.get('href'):
                    self.enrollment_url = result.get('href')
            else:
                # TODO: log errors
                print(response.status_code)
                print(response.content)
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

        return result


class Analysis(object):

    def __init__(self, token, app_model_id, consumer_id, payload=None):
        self.token = token
        self.app_model_id = app_model_id
        self.consumer_id = consumer_id
        if payload:
            # read-only objects do not need to set the payload
            # however if the payload is being set, it must be set right
            self.payload = self.set_payload(payload)
        self.task_name = None
        self.task_status = None
        self.intervals = []

    def set_payload(self, kwargs):
        """ setter method for attribute payload which validates and stores parameters for creating Analysis Endpoint
        :param kwargs: the parameters you want to set to while creating analysis endpoint
        """

        mandatory_fields = ['audioUrl']
        all_mandatory_fields_present = all([x in kwargs.keys() for x in mandatory_fields])

        try:
            if not all_mandatory_fields_present:
                error_text = 'Must provide all mandatory fields: ' + str(mandatory_fields)
                raise ImproperArgumentsException(error_text)
        except ImproperArgumentsException as e:
            print('Error while creating app model. ' + str(e))
            return None

        self.payload = kwargs
        return self.payload

    def start_task(self):
        """ starts the analysis process on the supplied .wav file, and returns the task_name (unique-id)
        """
        # could change this to use the consumer specific tokens in the future, with developer_id param
        headers = authorization_header()

        try:
            endpoint_analysis_url = g.config['URL_ANALYSIS']
            response = requests.post(endpoint_analysis_url, json=self.payload, headers=headers)
            if response and response.status_code == 200:
                result = json.loads(response.content)
                self.task_name = result.get('taskName')
                self.task_name = result.get('taskStatus')
                return result
            else:
                return response.status_code, response.content
        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    @staticmethod
    def check_status(task_name):
        """ returns the current status of an already started task
        """
        # could change this to use the consumer specific tokens in the future, with developer_id param
        headers = authorization_header()

        try:
            # for endpointAnalysis-id-get, the trailing word 'url' needs to be removed
            endpoint_analysis_url = re.sub(r'url$', str(task_name), g.config['URL_ANALYSIS'])
            response = requests.get(endpoint_analysis_url, headers=headers)

            if response and response.content:
                result = json.loads(response.content)
                return result
            else:
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def steps(self, intervals_with_phrases=False):
        """ combines both start_task and the check_status methods, if the status is not complete it re-attempts for
        n number of seconds indicated by REATTEMPT_CALLS_FOR config option
        ideally should return the task_name in the result with a task_status as 'completed'
        """
        result = None
        status_timestamp = None
        status_time_lapse = 0
        try:
            result = self.start_task()
            self.task_name = result.get('taskName')
            self.task_status = result.get('taskStatus')
            status_timestamp = datetime.now()
        except Exception as e:
            print('Analysis start task error:'.format(e))

        try:
            print('task_name: ' + str(self.task_name))
            print('task_status: ' + str(self.task_status))
            print('float(g.configREATTEMPT_CALLS_FOR: ' + str(float(g.config['REATTEMPT_CALLS_FOR'])))
            print('status_time_lapse: ' + str(status_time_lapse))

            while unicode(self.task_status) not in [u'completed', u'failed']\
                    and status_time_lapse < float(g.config['REATTEMPT_CALLS_FOR']):

                time.sleep(0.01)
                result = self.check_status(self.task_name)
                self.task_status = result.get('taskStatus')
                print('task_status: ' + str(self.task_status))
                status_time_lapse = (datetime.now() - status_timestamp).total_seconds()

                if unicode(self.task_status) == u'failed':
                    return None

        except AttributeError as e:
            print('Analysis check status error {}'.format(e))

        # set the member intervals to resulted intervals from end-point analysis
        self.intervals = result.get('intervals')
        print('Intervals: ' + str(self.intervals))
        if intervals_with_phrases:
            return self.intervals_with_phrases()

        return result

    def intervals_with_phrases(self):

        try:
            tg = TokenGetter()
            # a read only object of app model
            am = AppModel(tg.get_token())
            result = am.get(self.app_model_id)
            repetitions = result.get('enrollmentRepeats')
            vocabulary = result.get('vocabulary')

            # call to the generic helper function
            return h.merge_intervals_with_phrases(vocabulary, repetitions, self.intervals)

        except Exception as e:
            print("Could not generate intervals with phrases. " + str(e))

        return None


class Consumer(object):

    def __init__(self, token, payload=None):
        self.token = token
        if payload:
            # read-only objects do not need to set the payload
            self.payload = self.set_payload(payload)
        self.consumer_url = None
        self.consumer_token = None

    @property
    def consumer_id(self):
        if self.consumer_url:
            return h.parse_id_from_href(self.consumer_url)

    def set_payload(self, kwargs):
        """ setter method for attribute payload which validates and stores parameters while creating the consumer
        :param kwargs: the parameters you want to set to while creating a consumer
        """

        mandatory_fields = ['username', 'password', 'gender']
        all_mandatory_fields_present = all([x in kwargs.keys() for x in mandatory_fields])

        try:
            if not all_mandatory_fields_present:
                error_text = 'Must provide all mandatory fields: ' + str(mandatory_fields)
                raise ImproperArgumentsException(error_text)
        except ImproperArgumentsException as e:
            print('Error while creating app model. ' + str(e))
            return None

        self.payload = kwargs
        return self.payload

    def create(self):
        """
        create the app model
        :param
        payload (e.g. format) = {
            "gender": "M",
            "username": "theo",
            "password": "walcott"
        }
        consumer_id: an existing consumer_id
        :return: href for the created or updated consumer
        """
        headers = authorization_header()

        try:
            url = g.config['URL_CONSUMERS']

            if not self.payload:
                print('This seems to be a read-only object of Consumer, set the proper payload to create app model')
                return None

            response = requests.post(url, json=self.payload, headers=headers)
            if response.status_code == 201:
                self.consumer_url = json.loads(response.content).get('href')
                return self.consumer_id
            else:
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def update(self, consumer_id, payload_override=None):
        """
        update the app model's password field. Note: username and the gender are non editable fields
        :param
        payload (e.g. format) = {
            "password": "walcott360"
        }
        consumer_id: an existing consumer_id
        :return: href for the created or updated consumer
        """
        headers = authorization_header()
        try:
            url = g.config['URL_CONSUMERS'] + '/' + consumer_id

            if payload_override:
                self.payload = payload_override

            response = requests.post(url, json=self.payload, headers=headers)
            if response.status_code == 202:
                self.consumer_url = json.loads(response.content).get('href')
                return self.consumer_id
            else:
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def get(self, consumer_id):
        headers = authorization_header()

        try:
            url = g.config['URL_CONSUMERS'] + '/' + consumer_id

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
                if result.get('href'):
                    self.consumer_url = result.get('href')
            else:
                # TODO: log errors
                print(response.status_code)
                print(response.content)
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

        return result

    @staticmethod
    def get_all(limit=10, offset=0):
        headers = authorization_header()

        try:
            url = g.config['URL_CONSUMERS'] + '?limit=' + str(limit) + '&offset=' + str(offset)

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
                return result
            else:
                # TODO: log errors
                print(response.status_code)
                print(response.content)
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def get_token(self):
        """ returns consumer specific token based on the given user
        """
        headers = authorization_header()

        try:
            url = g.config['URL_CONSUMERS'] + '/token'

            response = requests.post(url, json=self.payload, headers=headers)
            self.consumer_token = json.loads(response.content).get('token')
            return self.consumer_token

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def delete(self, consumer_id):
        """ delete consumer with given id
        :param consumer_id:
        :return: result of deletion
        """
        headers = authorization_header()

        try:
            url = g.config['URL_CONSUMERS'] + '/' + consumer_id

            response = requests.delete(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
                if result.get('href'):
                    self.consumer_url = result.get('href')
            else:
                # TODO: log errors
                print(response.status_code)
                print(response.content)
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

        return result


class AppModel(object):
    """ The application model class that wraps Knurld API resources for application models
    Endpoint: https://api.knurld.io/v1/app-models
    """

    def __init__(self, token, payload=None):
        self.token = token
        if payload:
            # read-only objects do not need to set the payload
            self.payload = self.set_payload(payload)
        self.app_model_url = None

    @property
    def app_model_id(self):
        if self.app_model_url:
            return h.parse_id_from_href(self.app_model_url)

    def set_payload(self, kwargs):
        """ setter method for attribute payload which validates and stores parameters for app model creation
        :param kwargs: the parameters you want to set to while creating an app model
        """
        mandatory_fields = ['vocabulary', 'verificationLength', 'enrollmentRepeats']
        all_mandatory_fields_present = all([x in kwargs.keys() for x in mandatory_fields])

        try:
            if not all_mandatory_fields_present:
                error_text = 'Must provide all mandatory fields: ' + str(mandatory_fields)
                raise ImproperArgumentsException(error_text)
        except ImproperArgumentsException as e:
            print('Error while creating app model. ' + str(e))
            return None

        self.payload = kwargs
        return self.payload

    def create(self):
        """ create an app model using this method. Uses the payload dictionary set during object initialization
        """
        headers = authorization_header()

        try:
            url = g.config['URL_APP_MODELS']

            if not self.payload:
                print('This seems to be a read-only object of AppModel, set the proper payload to create app model')
                return None

            response = requests.post(url, json=self.payload, headers=headers)
            if response.status_code == 201:
                self.app_model_url = json.loads(response.content).get('href')
                return self.app_model_id
            else:
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def update(self, app_model_id, payload_override=None):
        """ update an app model using this method. Uses the payload dictionary set during object initialization
        :param app_model_id: existing app model id
        :param payload_override: a complete new payload developer might want to set
        """
        headers = authorization_header()

        try:
            url = g.config['URL_APP_MODELS'] + '/' + app_model_id
            if payload_override:
                self.payload = payload_override

            response = requests.post(url, json=self.payload, headers=headers)
            if response.status_code == 202:
                self.app_model_url = json.loads(response.content).get('href')
                return self.app_model_id
            else:
                # TODO: log errors
                print(response.status_code)
                print(response.content)
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

    def get(self, app_model_id):
        """ get an app model associated with a particular app_model_id.
        """
        headers = authorization_header()

        try:
            url = g.config['URL_APP_MODELS'] + '/' + app_model_id

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
                if result.get('href'):
                    self.app_model_url = result.get('href')
            else:
                # TODO: log errors
                print(response.status_code)
                print(response.content)
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

        return result

    @staticmethod
    def get_all(limit=10, offset=0):
        """ get a range of available app models
        TODO: provide pagination using offsets
        """
        headers = authorization_header()

        try:
            url = g.config['URL_APP_MODELS'] + '?limit=' + str(limit) + '&offset=' + str(offset)

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
            else:
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

        return result

    def delete(self, app_model_id):
        """ delete app model with given id
        :param app_model_id:
        :return:
        """
        headers = authorization_header()

        try:
            url = g.config['URL_APP_MODELS'] + '/' + app_model_id

            response = requests.delete(url, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.content)
                if result.get('href'):
                    self.app_model_url = result.get('href')
            else:
                # TODO: log errors
                print(response.status_code)
                print(response.content)
                return response.status_code, response.content

        except Exception as e:
            print('Could not perform the operation: ' + str(e))
            return None

        return result


class TokenGetter(object):
    """
    Makes sure you always get a valid token. Validates the current available token and renews it if it has expired
    """

    def __init__(self, token=None, expires=None):
        self._token = token
        self._token_timestamp = datetime.now()
        self._token_expires = expires if expires else g.config['TOKEN_EXPIRES']

    def _is_valid_token(self, token):
        """
        checking the validity of token based on the time it was issued last
        """
        try:
            time_lapse = (datetime.now() - self._token_timestamp).total_seconds()
            # print('time_lapse: ' + str(time_lapse))
            if time_lapse < self._token_expires:
                return True
            else:
                # print("Invalid token {} with timestamp {}".format(token, self._token_timestamp))
                return False
        except ValueError as e:
            print("Invalid token {} Details: {}".format(token, e))

        return False

    def renew_access_token(self):

        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'Host': g.config['URL_HOST']
                   }

        payload = {'client_id': g.config['CLIENT_ID'],
                   'client_secret': g.config['CLIENT_SECRET']
                   }

        response = requests.post(g.config['URL_ACCESS_TOKEN'], data=payload, headers=headers)
        self._token = json.loads(response.content).get('access_token')
        self._token_timestamp = datetime.now()

        return self._token

    def get_token(self):
        """
        caching the already fetched token for duration configed in TOKEN_EXPIRES before the token could be renewed again
        """
        # check the cached version of the token first
        self._token = g.region.get_or_create("this_hour_token", creator=self.renew_access_token,
                                             expiration_time=self._token_expires,
                                             should_cache_fn=self._is_valid_token)
        return self._token
