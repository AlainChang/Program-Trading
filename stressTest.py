from locust import TaskSet, task, HttpUser
import os
import json


class Website(HttpUser):

    def on_start(self):
        self.client.post(
            '/signin', {'email': 'nick@good.com', 'password': 'nick'})

    @task
    def index(self):
        self.client.get('/')


class WebsiteUser(TaskSet):
    host = 'http://127.0.0.1:5000'
    task_set = Website
    min_wait = 100
    max_wait = 500


if __name__ == "__main__":
    os.system('locust -f stressTest.py ')
