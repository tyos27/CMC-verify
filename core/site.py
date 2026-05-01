import asyncio
import time
import re
import discord
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from core.pending import take
from core.env import Env
from roblox.auth import trade, me, link
from roblox.group import inside
from store.links import put
from store.game_codes import get_by_roblox_name, attach_roblox_info
from discord_side.roles import refresh
from discord_side.client import bot

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

GROUP_NAME = "Roblox Main Group"

hits = {}
bad_hits = {}
oauth_starts = {}

STATE_RE = re.compile(r"^[A-Za-z0-9_\-]{20,200}$")
USER_ID_RE = re.compile(r"^[0-9]{1,30}$")


def stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def addr(req):
    ip = req.headers.get("x-forwarded-for")

    if ip:
        return ip.split(",")[0].strip()

    if req.client:
        return req.client.host

    return "unknown"


def sweep(bucket, ip, seconds):
    now = time.time()
    rows = bucket.get(ip, [])
    rows = [x for x in rows if now - x < seconds]
    rows.append(now)
    bucket[ip] = rows
    return rows


def limited(ip):
    normal = sweep(hits, ip, 60)
    return len(normal) > 40


def bad_limited(ip):
    bad = sweep(bad_hits, ip, 60)
    return len(bad) > 15


def bad(ip):
    sweep(bad_hits, ip, 60)


def valid_state(state):
    if not state:
        print("oauth invalid state: missing")
        return False

    state = str(state)

    if len(state) < 20 or len(state) > 200:
        print("oauth invalid state length:", len(state))
        return False

    if not STATE_RE.match(state):
        print("oauth invalid state chars:", state)
        return False

    return True


def valid_code(code):
    if not code:
        print("oauth invalid code: missing")
        return False

    code = str(code)

    if len(code) < 5 or len(code) > 2500:
        print("oauth invalid code length:", len(code))
        return False

    return True


def start_blocked(state):
    now = time.time()

    for key in list(oauth_starts.keys()):
        if now - oauth_starts[key] > 120:
            oauth_starts.pop(key, None)

    last = oauth_starts.get(state)

    if last and now - last < 2:
        return True

    oauth_starts[state] = now
    return False


def html(text, status=200):
    return HTMLResponse(text, status_code=status)


def game_allowed(req):
    key = req.headers.get("x-game-key")
    return key and key == Env.game_api_key


async def edit_verify_message(channel_id, message_id, title, desc, color):
    if not channel_id or not message_id:
        return

    try:
        channel = await bot.fetch_channel(int(channel_id))
        msg = await channel.fetch_message(int(message_id))

        embed = discord.Embed(
            title=title,
            description=desc,
            color=color
        )
        embed.set_footer(text=f"JAD Verify • {stamp()}")

        await msg.edit(embed=embed, view=None)
    except Exception as e:
        print("message edit failed:", e)


@app.get("/")
async def home():
    return html("JAD Verify", 200)


@app.get("/oauth/start")
async def oauth_start(req: Request):
    ip = addr(req)

    if limited(ip):
        return html("요청이 너무 많습니다. 잠시 후 다시 시도해주세요.", 429)

    if bad_limited(ip):
        return html("요청이 너무 많습니다. 잠시 후 다시 시도해주세요.", 429)

    state = req.query_params.get("state")

    print("oauth start received state:", state)
    print("oauth start SITE_URL:", Env.site_url)
    print("oauth start ROBLOX_REDIRECT_URI:", Env.roblox_redirect)

    if not state:
        return html("""
        <h2>JAD Verify</h2>
        <p>This is the Roblox OAuth entry point for JAD Verify.</p>
        <p>Please return to Discord and press the verification button.</p>
        """, 200)

    if not valid_state(state):
        bad(ip)
        return html("잘못된 인증 요청입니다.", 400)

    if start_blocked(state):
        return html("이미 인증 페이지로 이동했습니다. 잠시 후 다시 시도해주세요.", 429)

    try:
        url = link(state)
        print("oauth start redirecting to:", url)
        return RedirectResponse(url, status_code=302)
    except Exception as e:
        print("oauth start failed:", repr(e))
        return html("OAuth 시작 처리 중 오류가 발생했습니다. Railway 로그를 확인해주세요.", 500)

    return RedirectResponse(link(state), status_code=302)

@app.get("/oauth/callback")
async def callback(req: Request):
    ip = addr(req)

    if limited(ip):
        return html("요청이 너무 많습니다. 잠시 후 다시 시도해주세요.", 429)

    if bad_limited(ip):
        return html("요청이 너무 많습니다. 잠시 후 다시 시도해주세요.", 429)

    code = req.query_params.get("code")
    state = req.query_params.get("state")

    print("oauth callback received state:", state)
    print("oauth callback code exists:", bool(code))

    if not valid_state(state):
        bad(ip)
        return html("잘못된 인증 요청입니다.", 400)

    if not valid_code(code):
        bad(ip)
        return html("잘못된 요청입니다.", 400)

    data = take(state)

    if not data:
        bad(ip)
        return html("인증 시간이 만료되었습니다.\n디스코드에서 다시 시도해주세요!", 400)

    discord_id = data["discord_id"]
    channel_id = data.get("channel_id")
    message_id = data.get("message_id")

    try:
        token = trade(code)
        access_token = token.get("access_token")

        if not access_token:
            bad(ip)
            return html("Roblox 인증 정보를 가져오지 못했습니다.", 400)

        profile = me(access_token)

        roblox_id = profile.get("sub") or profile.get("id") or profile.get("user_id")

        roblox_name = (
            profile.get("preferred_username")
            or profile.get("name")
            or str(roblox_id)
        )

        roblox_display = (
            profile.get("display_name")
            or profile.get("displayName")
            or profile.get("nickname")
            or roblox_name
        )

        if not roblox_id:
            return html("Roblox 계정 정보를 가져오지 못했습니다.", 400)

        put(discord_id, roblox_id, roblox_name, roblox_display)

        if inside(int(roblox_id)):
            future = asyncio.run_coroutine_threadsafe(
                refresh(discord_id),
                bot.loop
            )

            ok, msg = future.result(timeout=15)

            if ok:
                asyncio.run_coroutine_threadsafe(
                    edit_verify_message(
                        channel_id,
                        message_id,
                        "✅ 연동 성공!",
                        f"<@{discord_id}>님, {roblox_name}으로 연동이 완료되었어요!",
                        0x57F287
                    ),
                    bot.loop
                ).result(timeout=15)

                return html("성공적으로 연동되었어요!\n이 사이트는 나가도 괜찮아요!")

            asyncio.run_coroutine_threadsafe(
                edit_verify_message(
                    channel_id,
                    message_id,
                    "인증 실패",
                    msg,
                    0xED4245
                ),
                bot.loop
            ).result(timeout=15)

            return html(msg, 400)

        asyncio.run_coroutine_threadsafe(
            edit_verify_message(
                channel_id,
                message_id,
                "⚠️ 인증 완료 - 그룹 미가입",
                f"<@{discord_id}>님, {roblox_name}으로 안전하게 연동이 완료되었어요!\n"
                f"하지만 Roblox 메인 그룹에 가입되어 있지 않아 역할 지급은 되지 않았어요.",
                0xFEE75C
            ),
            bot.loop
        ).result(timeout=15)

        return html("성공적으로 연동되었어요!\n이 사이트는 나가도 괜찮아요!")

    except Exception as e:
        print("callback failed:", e)
        return html("처리 중 오류가 발생했습니다.", 500)


@app.get("/api/game/session")
async def game_session(req: Request):
    if not game_allowed(req):
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)

    roblox_id = req.query_params.get("roblox_id")
    roblox_name = req.query_params.get("roblox_name")
    roblox_display_name = req.query_params.get("roblox_display_name")

    if not roblox_id or not USER_ID_RE.match(roblox_id):
        return JSONResponse({"ok": False, "error": "bad_roblox_id"}, status_code=400)

    if not roblox_name:
        return JSONResponse({"ok": False, "error": "missing_roblox_name"}, status_code=400)

    row = get_by_roblox_name(roblox_name)

    if not row:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)

    attach_roblox_info(
        row["id"],
        roblox_id,
        roblox_name,
        roblox_display_name or roblox_name
    )

    return JSONResponse({
        "ok": True,
        "discord_id": str(row["discord_id"]),
        "discord_name": row.get("discord_name") or "Unknown",
        "roblox_id": str(roblox_id),
        "roblox_name": roblox_name,
        "roblox_display_name": roblox_display_name or roblox_name,
        "code": row["code"]
    }, status_code=200)


@app.get("/privacy")
async def privacy():
    return html("""
    <h2>Privacy Policy</h2>
    <p>This service verifies Discord users with Roblox accounts.</p>
    <p>We store Discord ID, Roblox ID, Roblox username, and Roblox display name for verification.</p>
    <p>We do not collect Roblox passwords or Discord passwords.</p>
    """, 200)


@app.get("/terms")
async def terms():
    return html("""
    <h2>Terms of Service</h2>
    <p>This service is used for Roblox and Discord verification.</p>
    <p>You must only verify an account you own or are allowed to use.</p>
    """, 200)
