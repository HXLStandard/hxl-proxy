import requests

from hxl_proxy import app

def openid_user (code):
    """Look up a user from Humanitarian.ID based on an authorization token"""

    # Stage 1: get an access token
    params = {
        'client_id': app.config.get('HID_CLIENT_ID'),
        'client_secret': app.config.get('HID_CLIENT_SECRET'),
        'grant_type': 'authorization_code',
        'redirect_uri': app.config.get('HID_REDIRECT_URI'),
        'code': code
    }
    headers = {
        #'Authorization': 'Basic {secret}'.format(secret=app.config.get('HID_CLIENT_SECRET'))
    }
    response = requests.post(
        '{base_url}/oauth/access_token'.format(
            base_url = app.config.get('HID_BASE_URL')
        ), 
        headers=headers,
        data=params
    )

    if response.status_code != 200:
        raise Exception("Failed to get access token: {}".format(response.reason))

    # Stage 2: get the user data

    access_data = response.json()

    response = requests.get(
        '{base_url}/account.json?access_token={access_token}'.format(
            base_url = app.config.get('HID_BASE_URL'),
            access_token = requests.utils.quote(access_data['access_token'])
        )
    )

    return response.json()
