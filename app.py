import requests
import os

# API Configuration
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Query the root or base API
url = f"{API_HOST}/"
headers = {"X-Domino-Api-Key": API_KEY}

response = requests.get(url, headers=headers)
print("Response Status Code:", response.status_code)
print("Response Text:", response.text)