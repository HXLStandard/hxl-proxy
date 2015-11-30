import requests
import urllib

def openid_user (code):
    params = {
        'grant_type': 'authorization_code',
        'redirect': 'example.org',
        'code': code
    }
    headers = {
        'Authorization': 'Basic {secret}'.format(secret='MbmXHTxj0rmiuiiJ1YC4V2bQ81O_m5x3HQnX7GdYf9c')
    }
    response = requests.post(
        'http://auth.dev.humanitarian.id/oauth/access_token', 
        auth=requests.auth.HTTPBasicAuth('hid', 'dev'),
        headers=headers,
        data=params
    )
    return response.text


