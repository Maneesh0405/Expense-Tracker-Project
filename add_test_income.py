import requests
import json
import logging
from datetime import datetime

BASE_URL = 'http://localhost:5000/api'

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def add_income():
    # 1. Login to get user ID (using demo credentials)
    logging.info("Logging in as demo...")
    try:
        response = requests.post(f'{BASE_URL}/auth/login', json={
            'username': 'demo',
            'password': 'demo123'
        })
        
        if response.status_code != 200:
            # Try registering if login fails
            logging.warning("Login failed, trying to register...")
            reg_response = requests.post(f'{BASE_URL}/auth/register', json={
                'username': 'demo',
                'email': 'demo@example.com',
                'password': 'demo123'
            })
            if reg_response.status_code == 201:
                logging.info("Registered demo user.")
                # Login again
                response = requests.post(f'{BASE_URL}/auth/login', json={
                    'username': 'demo',
                    'password': 'demo123'
                })
            else:
                logging.error(f"Registration failed: {reg_response.text}")
                return

        user_data = response.json()
        user_id = str(user_data['user']['id'])
        logging.info(f"Logged in. User ID: {user_id}")

        # 2. Add 10000 Income
        headers = {'User-Id': user_id, 'Content-Type': 'application/json'}
        income_data = {
            'amount': 10000,
            'description': 'Manual Entry 10000',
            'date': datetime.now().isoformat()
        }

        logging.info("Adding income 10000...")
        response = requests.post(f'{BASE_URL}/income', json=income_data, headers=headers)
        
        if response.status_code == 201:
            logging.info("Successfully added 10000 income!")
            logging.debug(response.json())
        else:
            logging.error(f"Failed to add income: {response.status_code} - {response.text}")

    except Exception as e:
        logging.exception(f"An error occurred: {e}")

if __name__ == '__main__':
    add_income()
