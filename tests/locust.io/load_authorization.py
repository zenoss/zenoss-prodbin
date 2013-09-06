#!/usr/bin/env python

from locust import Locust, TaskSet, task

## Authorization.py defines test cases to benchmark the ZAuth service. The test
#  cases are written using Locust IO (http://locust.io/).  See ../README for
#  directions.

class AuthorizationTaskSet(TaskSet):

    @task(9)
    class SuccessfulTaskSet(TaskSet):
        token = None

        def on_start(self):
            credentials = {"login":"admin", "password":"zenoss"}
            response = self.client.post( "/authorization/login", credentials)
            self.token = response.json

        @task
        def validateSuccessWithId(self):
            tokenId = self.token['id']
            self.client.post( "/authorization/validate", {'id':tokenId})

        @task
        def validateSuccessWithHeader(self):
            tokenId = self.token['id']
            self.client.post( "/authorization/validate", headers={'X-ZAuth-Token':tokenId})

    @task(1)
    class FailureTaskSet(TaskSet):
        @task
        def loginFailureMissingCredentials(self):
            with self.client.post( "/authorization/login", catch_response=True) as response:
                if response.status_code == 401:
                    response.success()

        @task
        def loginFailureInvalidCredentials(self):
            credentials = {"login":"zenoss", "password":"invalid"}
            with self.client.post( "/authorization/login", credentials, catch_response=True) as response:
                if response.status_code == 401:
                    response.success()

        @task
        def validateFailureMissingId(self):
            with self.client.post( "/authorization/validate", catch_response=True) as response:
                if response.status_code == 401:
                    response.success()

        @task
        def validateFailureExpiredTokenId(self):
            with self.client.post( "/authorization/validate", {"id":"0"}, catch_response=True) as response:
                if response.status_code == 401:
                    response.success()

class AuthorizationSimulator(Locust):
    task_set = AuthorizationTaskSet
    min_wait = 1000
    max_wait = 5000
