import requests
import random
import string

from bs4 import BeautifulSoup

class Label_studio_web:
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
    }
    session = None
    url = 'http://localhost:8085'
    user = {
        'email': '',
        'password': ''
    }

    def __init__(self, url: str = '', headers: dict = {}):
        self.url = url or self.url
        self.headers = headers or self.headers
        self.session = requests.Session()

    def get_csrf_token(self) -> str:
        response = self.session.get(f'{self.url}/user/login')
        if response.status_code != 200:
            raise Exception('Couldn\'t get the CSRF token!')
        
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']

        if not csrf_token:
            raise Exception('CSRF token not found on the page!')
        
        return csrf_token

    def create_user(self, email: str = '', password: str = '') -> str:
        csrf_token = self.get_csrf_token()

        data = {
            'csrfmiddlewaretoken': csrf_token,  # Add the CSRF token to the form data
            'email': email or self._generate_random_email(),
            'password': password or ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)),
            'how_find_us': 'Search engine',
            'elaborate': '',
            'allow_newsletters': False
        }

        signup_response = self.session.post(
            f'{self.url}/user/signup/?&next=/projects/',
            data=data,
            headers=self.headers
        )
        
        if signup_response.status_code != 200:
            raise Exception('Couldn\'t create the user!', signup_response, signup_response.text)

        self.user['email'] = data.get('email')
        self.user['password'] = data.get('password')

        return csrf_token
    
    def login(self, csrf_token: str = '') -> bool:
        csrf_token = self.get_csrf_token()

        data = {
            'csrfmiddlewaretoken': csrf_token,  # Add the CSRF token to the form data
            'email': self.user.get('email'),
            'password': self.user.get('password'),
            'persist_session': 'on'
        }

        signin_response = self.session.post(
            f'{self.url}/user/login/?next=/projects/', 
            data=data, 
            headers=self.headers
        )
    
        if signin_response.status_code != 200:
            raise Exception('Couldn\'t create the user!', signin_response, signin_response.text)
        
        return True
        
    def get_api_token(self) -> str:
        csrf_token = self.create_user()
        if not csrf_token:
            raise Exception('Couldn\'t create an user!')
        
        '''if not self.login(csrf_token):
            raise Exception('Couldn\'t login with the user!')'''

        account_response = self.session.get(f'{self.url}/user/account')

        soup = BeautifulSoup(account_response.text, 'html.parser')
        api_token = soup.find('input', {'id': 'access_token'})['value']

        if not api_token:
            raise Exception('API token not found on the page!', account_response, account_response.text)
        
        return api_token

    def _generate_random_email(self) -> str:
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

        domains = ['gmail', 'yahoo', 'outlook', 'example']
        domain = random.choice(domains)

        email = f'{username}@{domain}.com'
        return email