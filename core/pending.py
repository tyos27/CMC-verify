items = {}


def hold(state, discord_id, channel_id, message_id, discord_name=None):
    items[state] = {
        "discord_id": discord_id,
        "channel_id": channel_id,
        "message_id": message_id,
        "discord_name": discord_name
    }


def put(state, discord_id, channel_id, message_id, discord_name=None):
    hold(state, discord_id, channel_id, message_id, discord_name)


def take(state):
    return items.pop(state, None)
