import requests

from hxl_proxy import app

def openid_user (code):
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
        'http://auth.dev.humanitarian.id/oauth/access_token', 
        headers=headers,
        data=params
    )
    return response.text


