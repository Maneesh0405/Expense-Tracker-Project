import requests
import json
from datetime import datetime

BASE_URL = 'http://localhost:5000/api'

def add_income():
    # 1. Login to get user ID (using demo credentials from index.html)
    print("Logging in as demo...")
    try:
        response = requests.post(f'{BASE_URL}/auth/login', json={
            'username': 'demo',
            'password': 'demo123'
        })
        
        if response.status_code != 200:
            # Try registering if login fails
            print("Login failed, trying to register...")
            reg_response = requests.post(f'{BASE_URL}/auth/register', json={
                'username': 'demo',
                'email': 'demo@example.com',
                'password': 'demo123'
            })
            if reg_response.status_code == 201:
                print("Registered demo user.")
                # Login again
                response = requests.post(f'{BASE_URL}/auth/login', json={
                    'username': 'demo',
                    'password': 'demo123'
                })
            else:
                print(f"Registration failed: {reg_response.text}")
                return

        user_data = response.json()
        user_id = str(user_data['user']['id'])
        print(f"Logged in. User ID: {user_id}")

        # 2. Add 10000 Income
        headers = {'User-Id': user_id, 'Content-Type': 'application/json'}
        income_data = {
            'amount': 10000,
            'description': 'Manual Entry 10000',
            'date': datetime.now().isoformat()
        }

        print("Adding income 10000...")
        response = requests.post(f'{BASE_URL}/income', json=income_data, headers=headers)
        
        if response.status_code == 201:
            print("Successfully added 10000 income!")
            print(response.json())
        else:
            print(f"Failed to add income: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    add_income()
