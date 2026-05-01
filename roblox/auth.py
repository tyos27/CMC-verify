from urllib.parse import urlencode
import requests
from core.env import Env


base = "https://apis.roblox.com/oauth/v1"


def link(state):
    return base + "/authorize?" + urlencode({
        "client_id": Env.roblox_client_id,
        "response_type": "code",
        "redirect_uri": Env.roblox_redirect,
        "scope": "openid profile",
        "state": state,
    })


def start_link(state):
    return Env.site_url.rstrip("/") + "/oauth/start?" + urlencode({
        "state": state
    })


def trade(code):
    r = requests.post(base + "/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": Env.roblox_redirect,
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
