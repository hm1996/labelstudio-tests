import os
import csv
import random
import unittest

from utils import get_label_studio_app_pod_info

from minio import Minio

from label_studio_sdk.client import LabelStudio
from label_studio_sdk.label_interface import LabelInterface
from label_studio_sdk.label_interface.create import choices

from label_studio_web import Label_studio_web

from kubernetes import client, config

LABEL_STUDIO_URL = os.getenv('LABELS_TUDIO_URL', 'http://localhost:8085')
HELM_RELEASE = os.getenv('HELM_RELEASE', 'label-studio')
HELM_RELEASE_NAMESPACE = os.getenv('HELM_RELEASE_NAMESPACE', 'default')
LABEL_STUDIO_APP_NAME = os.getenv('LABEL_STUDIO_APP_NAME', 'ls-app')
KUBE_CONFIG_PATH = os.getenv('KUBE_CONFIG_PATH', '/home/humar/.kube/config')
MINIO_URL = os.getenv('MINIO_URL', 'localhost:9000')
MINIO_EXTERNAL_URL = os.getenv('MINIO_EXTERNAL_URL', 'http://minio-1737413701.minio.svc.cluster.local:9000')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'label-studio-bucket')
MINIO_KEY_ID = os.getenv('MINIO_KEY_ID', 'yPHcPxXxbruCjhQNM9O7')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'miYc42jQTCc7Sdk540yYLDm9uJdwl3ks8y4cE9Lt')

print(MINIO_KEY_ID, MINIO_SECRET_KEY, MINIO_URL, MINIO_BUCKET)

config.load_kube_config(KUBE_CONFIG_PATH)

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

        print('User created:', user)

        self.assertIsNotNone(user)

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

        print('Project created:', project)

        self.assertIsNotNone(project)

        TestLabelStudioAPI.project_id = project.id

    @unittest.skipIf(MINIO_KEY_ID == '', 'Minio access key is not provided')
    @unittest.skipIf(MINIO_SECRET_KEY == '', 'Minio secret key is not provided')
    def test_minio_connection(self):
        self.assertNotEqual(self.api_key, '')
        self.assertIsNotNone(self.label_studio_client)
        self.assertNotEqual(self.project_id, -1)

        client = Minio(
            endpoint=MINIO_URL,
            access_key=MINIO_KEY_ID,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )

        found = client.bucket_exists(MINIO_BUCKET)
        if not found:
            client.make_bucket(MINIO_BUCKET)
            print("Created bucket:", MINIO_BUCKET)
        else:
            print("Bucket", MINIO_BUCKET, "already exists")

        result = self.label_studio_client.export_storage.s3.create(
            aws_access_key_id=MINIO_KEY_ID,
            aws_secret_access_key=MINIO_SECRET_KEY,
            bucket=MINIO_BUCKET,
            can_delete_objects=True,
            project=self.project_id,
            s3endpoint=MINIO_EXTERNAL_URL,
            title='MinIO connection',
            request_options={'verify': False}
        )

        print('MinIO connection:', result)
        self.assertIsNotNone(result)

    def test_data_importing(self):
        self.assertNotEqual(self.api_key, '')
        self.assertIsNotNone(self.label_studio_client)
        self.assertNotEqual(self.project_id, -1)

        tasks = []
        with open('./data/IMDB_train_unlabeled_0_50.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            tasks = [{ 'text': row['review'] } for row in reader]

        imports = self.label_studio_client.projects.import_tasks(
            id=self.project_id,
            request=tasks
        )

        print('Task imported:', imports)

        self.assertIsNotNone(imports)
        self.assertEqual(imports.task_count, 49)

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

    @unittest.skipIf(MINIO_KEY_ID == '', 'Minio access key is not provided')
    @unittest.skipIf(MINIO_SECRET_KEY == '', 'Minio secret key is not provided')
    def test_minio_labels_exporting(self):
        self.assertNotEqual(self.api_key, '')
        self.assertIsNotNone(self.label_studio_client)
        self.assertNotEqual(self.project_id, -1)

        client = Minio(
            endpoint=MINIO_URL,
            access_key=MINIO_KEY_ID,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )

        objects = list(client.list_objects(MINIO_BUCKET))

        self.assertNotEqual(objects, [])

        objects_names = [obj.object_name for obj in objects]

        print('Objects in bucket:', objects_names)
        

    def test_data_cleaning(self):
        self.assertNotEqual(self.api_key, '')
        self.assertIsNotNone(self.label_studio_client)
        self.assertNotEqual(self.project_id, -1)
        # self.assertNotEqual(self.user_id, -1)

        data = self.label_studio_client.projects.delete(id=self.project_id)
        
        print(data)
        data = self.label_studio_client.users.delete(id=self.user_id)
        
        print(data)
        pass

if __name__ == '__main__':
    suite = unittest.TestSuite()

    suite.addTest(TestLabelStudioRelease('test_label_studio_pod_running'))
    suite.addTest(TestLabelStudioRelease('test_label_studio_open_ports'))
    
    suite.addTest(TestLabelStudioAPI('test_user_creation'))
    suite.addTest(TestLabelStudioAPI('test_project_creation'))
    suite.addTest(TestLabelStudioAPI('test_minio_connection'))
    suite.addTest(TestLabelStudioAPI('test_data_importing'))
    suite.addTest(TestLabelStudioAPI('test_tasks_running'))
    suite.addTest(TestLabelStudioAPI('test_labels_exporting'))
    suite.addTest(TestLabelStudioAPI('test_minio_labels_exporting'))
    suite.addTest(TestLabelStudioAPI('test_data_cleaning'))

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)