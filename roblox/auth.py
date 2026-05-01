from urllib.parse import urlencode
import requests
from core.env import Env


base = "https://apis.roblox.com/oauth/v1"


def callback_url():
    return Env.site_url.rstrip("/") + "/oauth/callback"


def link(state):
    redirect_uri = callback_url()

    print("oauth authorize redirect_uri:", redirect_uri)

    return base + "/authorize?" + urlencode({
        "client_id": Env.roblox_client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "openid profile",
        "state": state,
    })


def start_link(state):
    url = Env.site_url.rstrip("/") + "/oauth/start?" + urlencode({
        "state": state
    })

    print("oauth start url:", url)

    return url


def trade(code):
    redirect_uri = callback_url()

    print("oauth token redirect_uri:", redirect_uri)

    r = requests.post(base + "/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": Env.roblox_client_id,
        "client_secret": Env.roblox_client_secret,
    }, timeout=15)

    r.raise_for_status()

    return r.json()


def me(access_token):
    r = requests.get(base + "/userinfo", headers={
        "Authorization": f"Bearer {access_token}"
    }, timeout=15)

    r.raise_for_status()

    return r.json()
