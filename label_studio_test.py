import os
import csv
import json
import random
import unittest

from utils import get_label_studio_app_pod_info

from label_studio_sdk.client import LabelStudio
from label_studio_sdk.label_interface import LabelInterface
from label_studio_sdk.label_interface.create import choices

from label_studio_web import Label_studio_web

from kubernetes import client, config

LABEL_STUDIO_URL = os.getenv('LABELS_TUDIO_URL', 'http://localhost:8085')
HELM_RELEASE = os.getenv('HELM_RELEASE', 'label-studio')
HELM_RELEASE_NAMESPACE = os.getenv('HELM_RELEASE_NAMESPACE', 'default')
LABEL_STUDIO_APP_NAME = 'ls-app'

config.load_kube_config()

kubernetes_client = client.CoreV1Api()

label_studio_web = Label_studio_web()

class TestLabelStudioRelease(unittest.TestCase):
    pod_info = {}

    def test_label_studio_pod_running(self):
        self.pod_info = get_label_studio_app_pod_info(
            kubernetes_client, 
            HELM_RELEASE, 
            HELM_RELEASE_NAMESPACE, 
            LABEL_STUDIO_APP_NAME
        )
        self.assertIsNotNone(self.pod_info)
        self.assertIn(LABEL_STUDIO_APP_NAME, self.pod_info.get('name'))

    def test_label_studio_open_ports(self):
        pass

class TestLabelStudioAPI(unittest.TestCase):
    api_key = ''
    label_studio_client = None
    user_id = -1
    project_id = -1

    def test_user_creation(self):
        try:
            TestLabelStudioAPI.api_key = label_studio_web.get_api_token()
        except Exception as e:
            pass
        
        self.assertNotEqual(self.api_key, '')

        TestLabelStudioAPI.label_studio_client = LabelStudio(
            base_url=LABEL_STUDIO_URL, 
            api_key=self.api_key
        )

        user = self.label_studio_client.users.create(
            first_name='Dummy',
            last_name='User',
            username='dummy-user',
            email='dummy@example.com'
        )

        print('-----------------------------------------------------------')
        print('User created:', user)

        self.assertIsNotNone(user)
        # self.assertIn('id', user)

        TestLabelStudioAPI.user_id = user.id

    def test_project_creation(self):
        self.assertNotEqual(self.api_key, '')
        self.assertIsNotNone(self.label_studio_client)

        label_config = LabelInterface.create({
            'text': 'Text',
            'label': choices(['Positive', 'Negative'])
        })

        project = self.label_studio_client.projects.create(
            title='IMDB Sentiment Analysis',
            label_config=label_config
        )

        print('-----------------------------------------------------------')
        print('Project created:', project)

        self.assertIsNotNone(project)

        TestLabelStudioAPI.project_id = project.id

    def test_data_importing(self):
        self.assertNotEqual(self.api_key, '')
        self.assertIsNotNone(self.label_studio_client)
        self.assertNotEqual(self.project_id, -1)

        tasks = []
        with open('./data/IMDB_train_unlabeled_100.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            tasks = [{ 'text': row['review'] } for row in reader]

        imports = self.label_studio_client.projects.import_tasks(
            id=self.project_id,
            request=tasks
        )

        print('-----------------------------------------------------------')
        print('Task imported:', imports)

        self.assertIsNotNone(imports)
        self.assertEqual(imports.task_count, 98)

    def test_tasks_running(self):
        self.assertNotEqual(self.api_key, '')
        self.assertIsNotNone(self.label_studio_client)
        self.assertNotEqual(self.project_id, -1)

        annotation = [{
            'from_name': 'label',
            'to_name': 'text',
            'origin': 'manual',
            'type': 'choices',
            'value': {
                'choices': [ 'Negative' ]
            }
        }]

        tasks = self.label_studio_client.tasks.list(project=self.project_id)

        self.assertIsNotNone(tasks)

        size = len(list(tasks))
        count = 1
        for task in tasks:
            annotation[0]['value']['choices'] = [ random.choice(['Negative', 'Positive']) ]
            result = self.label_studio_client.annotations.create(
                id=task.id,
                result=annotation
            )

            self.assertIsNotNone(result)

            print(f'Annotating {count} of {size}')

            count += 1
        
    def test_labels_exporting(self):
        self.assertNotEqual(self.api_key, '')
        self.assertIsNotNone(self.label_studio_client)
        self.assertNotEqual(self.project_id, -1)

        exports = list(self.label_studio_client.projects.exports.create_export(
            id=self.project_id,
        ))

        with open('./results.json', 'w') as f:
            for chown in exports:
                f.write(chown.decode('utf-8'))

        self.assertNotEqual(exports, '')

    def test_data_cleaning(self):
        self.assertNotEqual(self.api_key, '')
        self.assertIsNotNone(self.label_studio_client)
        self.assertNotEqual(self.project_id, -1)
        self.assertNotEqual(self.user_id, -1)

        data = self.label_studio_client.projects.delete(id=self.project_id)
        print('-----------------------------------------------------------')
        print(data)
        data = self.label_studio_client.users.delete(id=self.user_id)
        print('-----------------------------------------------------------')
        print(data)
        pass

if __name__ == '__main__':
    suite = unittest.TestSuite()

    suite.addTest(TestLabelStudioRelease('test_label_studio_pod_running'))
    suite.addTest(TestLabelStudioRelease('test_label_studio_open_ports'))
    
    suite.addTest(TestLabelStudioAPI('test_user_creation'))
    suite.addTest(TestLabelStudioAPI('test_project_creation'))
    suite.addTest(TestLabelStudioAPI('test_data_importing'))
    suite.addTest(TestLabelStudioAPI('test_tasks_running'))
    suite.addTest(TestLabelStudioAPI('test_labels_exporting'))
    suite.addTest(TestLabelStudioAPI('test_data_cleaning'))

    runner = unittest.TextTestRunner()
    runner.run(suite)