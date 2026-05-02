import secrets
import discord
from discord.ui import View, Button, Modal, TextInput
from core.pending import put as hold
from roblox.auth import start_link
from store.links import pull, put
from store.game_codes import create_discord_pending, consume_code
from discord_side.roles import refresh
from roblox.group import inside
from datetime import datetime


def stamp():
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M")


def panel(title, desc, color=0x2f3136):
    e = discord.Embed(
        title=title,
        description=desc,
        color=color
    )
    e.set_footer(
        text=f"JAD Verify • {stamp()}"
    )
    return e


class TimedView(View):
    def __init__(self, owner_id):
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.message = None
        self.closed = False

    def close(self):
        self.closed = True
        self.stop()

    async def on_timeout(self):
        if self.closed:
            return

        try:
            if not self.message:
                return

            msg = await self.message.channel.fetch_message(self.message.id)

            if not msg.components:
                return

            await msg.edit(
                embed=panel(
                    "❌ 시간 초과",
                    "계정 연동 시간이 초과되었습니다. 다시 시도해주세요.",
                    0xed4245
                ),
                view=None
            )
        except Exception:
            pass


class UrlButton(Button):
    def __init__(self, owner_id, channel_id=None, message_id=None):
        state = secrets.token_urlsafe(32)
        hold(state, owner_id, channel_id, message_id)

        super().__init__(
            label="인증하기",
            style=discord.ButtonStyle.link,
            url=start_link(state)
        )


class GameLinkButton(Button):
    def __init__(self):
        super().__init__(
            label="인증 게임 바로가기",
            style=discord.ButtonStyle.link,
            url="https://www.roblox.com/games/126742579358323/JS-Authentication-Center-JS"
        )


class Gate(TimedView):
    def __init__(self, owner_id):
        super().__init__(owner_id)
        self.add_item(StartButton(owner_id))


class StartButton(Button):
    def __init__(self, owner_id):
        super().__init__(
            label="인증하기",
            style=discord.ButtonStyle.green
        )
        self.owner_id = owner_id

    async def callback(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=panel(
                    "⚠️ 권한 부족",
                    "본인만 사용할 수 있습니다.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        self.view.close()

        old = pull(self.owner_id)

        if old:
            v = ConfirmView(self.owner_id)

            await interaction.response.edit_message(
                embed=panel(
                    ":scroll: 기존 인증 기록",
                    f"`{old['roblox_name']}` 계정으로 연동되어 있습니다.\n이 계정으로 계속할까요?",
                    0x5865f2
                ),
                view=v
            )

            v.message = interaction.message
            return

        v = MethodView(self.owner_id)

        await interaction.response.edit_message(
            embed=panel(
                "✅ 인증 방식 선택",
                "**1. OAuth 인증**\nRoblox 공식 로그인 페이지를 통해 바로 인증합니다.\n"
                "**2. 게임 코드 인증**\nRoblox 계정 닉네임을 입력한 뒤 인증용 게임에 접속해서 코드를 확인합니다.",
                0x57f287
            ),
            view=v
        )

        v.message = interaction.message


class MethodView(TimedView):
    def __init__(self, owner_id):
        super().__init__(owner_id)
        self.add_item(OAuthMethodButton(owner_id))
        self.add_item(GameCodeMethodButton(owner_id))


class OAuthMethodButton(Button):
    def __init__(self, owner_id):
        super().__init__(
            label="1️⃣",
            style=discord.ButtonStyle.blurple
        )
        self.owner_id = owner_id

    async def callback(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=panel(
                    "⚠️ 권한 부족",
                    "본인만 사용할 수 있습니다.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        self.view.close()

        v = TimedView(self.owner_id)
        v.add_item(
            UrlButton(
                self.owner_id,
                interaction.channel.id,
                interaction.message.id
            )
        )

        await interaction.response.edit_message(
            embed=panel(
                "✅ Roblox 인증",
                "아래 버튼을 눌러 Roblox 계정을 연동하세요!",
                0x57f287
            ),
            view=v
        )

        v.message = interaction.message


class GameCodeMethodButton(Button):
    def __init__(self, owner_id):
        super().__init__(
            label="2️⃣",
            style=discord.ButtonStyle.green
        )
        self.owner_id = owner_id

    async def callback(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=panel(
                    "⚠️ 권한 부족",
                    "본인만 사용할 수 있습니다.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            RobloxNameModal(
                self.owner_id,
                interaction.message
            )
        )


class RobloxNameModal(Modal):
    def __init__(self, owner_id, target_message):
        super().__init__(title="계정 인증")
        self.owner_id = owner_id
        self.target_message = target_message

        self.roblox_name = TextInput(
            label="인증하려는 Roblox 계정 닉네임",
            placeholder="예: tyos",
            min_length=3,
            max_length=20,
            required=True
        )

        self.add_item(self.roblox_name)

    async def on_submit(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=panel(
                    "⚠️ 권한 부족",
                    "본인만 사용할 수 있습니다.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        roblox_name = str(self.roblox_name.value).strip()

        create_discord_pending(
            interaction.user.id,
            str(interaction.user),
            roblox_name
        )

        v = TimedView(self.owner_id)
        v.add_item(GameLinkButton())
        v.add_item(EnterCodeButton(self.owner_id))

        await self.target_message.edit(
            embed=panel(
                "✅ 인증 대기 중",
                f"인증하려는 Roblox 계정: `{roblox_name}`\n\n"
                "이제 인증용 [Roblox 게임](https://www.roblox.com/games/126742579358323/JS-Authentication-Center-JS)에 해당 계정으로 접속하세요.\n"
                "게임 화면에 표시되는 6자리 코드를 확인한 뒤 아래 **코드 입력** 버튼을 눌러 입력해주세요!\n\n"
                "코드는 2분 동안만 유효해요!",
                0x57f287
            ),
            view=v
        )

        v.message = self.target_message

        await interaction.followup.send(
            embed=panel(
                "✅ 요청 완료",
                "인증용 Roblox 게임에 접속한 뒤, 표시되는 6자리 코드를 입력하세요.",
                0x57f287
            ),
            ephemeral=True
        )


class EnterCodeButton(Button):
    def __init__(self, owner_id):
        super().__init__(
            label="코드 입력",
            style=discord.ButtonStyle.gray
        )
        self.owner_id = owner_id

    async def callback(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=panel(
                    "⚠️ 권한 부족",
                    "본인만 사용할 수 있습니다.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            GameCodeModal(
                self.owner_id,
                interaction.message
            )
        )


class GameCodeModal(Modal):
    def __init__(self, owner_id, target_message):
        super().__init__(title="게임 코드 입력")
        self.owner_id = owner_id
        self.target_message = target_message

        self.code = TextInput(
            label="Roblox 게임에 표시된 6자리 코드",
            placeholder="예: 123456",
            min_length=6,
            max_length=7,
            required=True
        )

        self.add_item(self.code)

    async def on_submit(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=panel(
                    "⚠️ 권한 부족",
                    "본인만 사용할 수 있습니다.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        clean = str(self.code.value).replace(" ", "").strip()

        if not clean.isdigit() or len(clean) != 6:
            await interaction.followup.send(
                embed=panel(
                    "❌ 잘못된 코드",
                    "6자리 숫자 코드를 입력해주세요.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        row = consume_code(clean)

        if not row:
            await interaction.followup.send(
                embed=panel(
                    "❌ 인증 실패",
                    "코드가 없거나 만료되었습니다. Roblox 게임에서 새 코드를 받아주세요.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        if str(row.get("discord_id")) != str(interaction.user.id):
            await interaction.followup.send(
                embed=panel(
                    "❌ 인증 실패",
                    "이 코드는 다른 Discord 계정의 인증 코드입니다.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        if not row.get("roblox_id"):
            await interaction.followup.send(
                embed=panel(
                    "❌ 인증 실패",
                    "Roblox 게임 접속 확인이 아직 완료되지 않았습니다. 게임에 먼저 접속해서 코드를 확인해주세요.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        put(
            interaction.user.id,
            row["roblox_id"],
            row["roblox_name"],
            row.get("roblox_display_name")
        )

        if inside(int(row["roblox_id"])):
            ok, msg = await refresh(interaction.user.id)

            await self.target_message.edit(
                embed=panel(
                    "✅ 인증 완료",
                    msg,
                    0x57f287 if ok else 0xfee75c
                ),
                view=None
            )

            try:
                await interaction.delete_original_response()
            except Exception:
                pass

            return

        await self.target_message.edit(
            embed=panel(
                "⚠️ 인증 저장 완료",
                f"`{row['roblox_name']}` 계정 연동은 완료되었어요!\n하지만 Roblox 그룹에 가입되어 있지 않아 역할 지급은 되지 않았어요!",
                0xfee75c
            ),
            view=None
        )

        try:
            await interaction.delete_original_response()
        except Exception:
            pass


class ConfirmView(TimedView):
    def __init__(self, owner_id):
        super().__init__(owner_id)
        self.add_item(YesButton(owner_id))
        self.add_item(NoButton(owner_id))


class YesButton(Button):
    def __init__(self, owner_id):
        super().__init__(
            label="✅",
            style=discord.ButtonStyle.green
        )
        self.owner_id = owner_id

    async def callback(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=panel(
                    "⚠️ 권한 부족",
                    "본인만 사용할 수 있습니다.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        self.view.close()

        ok, msg = await refresh(self.owner_id)

        await interaction.response.edit_message(
            embed=panel(
                "✅ 인증 완료",
                msg,
                0x57f287 if ok else 0xed4245
            ),
            view=None
        )


class NoButton(Button):
    def __init__(self, owner_id):
        super().__init__(
            label="❌",
            style=discord.ButtonStyle.red
        )
        self.owner_id = owner_id

    async def callback(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=panel(
                    "⚠️ 권한 부족",
                    "본인만 사용할 수 있습니다.",
                    0xed4245
                ),
                ephemeral=True
            )
            return

        self.view.close()

        v = MethodView(self.owner_id)

        await interaction.response.edit_message(
            embed=panel(
                "⚠️ 재인증",
                "새 Roblox 계정으로 다시 인증할 방식을 선택해주세요.\n"
                "**1. OAuth 인증**\nRoblox 공식 로그인 페이지를 통해 바로 인증합니다.\n"
                "**2. 게임 코드 인증**\nRoblox 닉네임을 입력한 뒤 인증용 게임에 접속해서 코드를 확인합니다.",
                0xfee75c
            ),
            view=v
        )

        v.message = interaction.message
