import socket
import discord
import json
import valve.rcon
from discord.ext import commands, tasks
from jishaku.functools import executor_function
from valve.source.a2s import ServerQuerier
from steam.steamid import SteamID

@executor_function
def load_json(json_path):
    with open(json_path, 'r') as file:
        return json.load(file)

@executor_function
def dump_json(json_path, dir):
    with open(json_path, 'w') as file:
        json.dump(dir, file, indent=2)

with open('./json/config.json', 'r') as file:
    CONFIG = json.load(file)
    SERVER_PUBLIC_IP = CONFIG["ip"]
    PORT = CONFIG["port"]
    PREFIX = CONFIG["command_prefix"]

SERVER_LOCAL_IP = socket.gethostbyname(socket.gethostname()) # Get local ip

ADDR = (SERVER_LOCAL_IP, PORT)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(ADDR)
sock.settimeout(0.001) # Recv Timeout

def parselog(log):
    if 'say_team' in log:
        log = log[27:].split(" say_team ")
        team_show = "<team>"
    else:
        team_show = ""
        log = log[27:].split(" say ")
    chat_info = log[0].split("><")
    if len(chat_info) > 4:
        log_send = f"{log[0]} : {log[1]}"
    else:
        misc = chat_info[0].split("<")
        name = misc[0]
        player_id = misc[1]
        steam_id= chat_info[1]
        steam_id_aux = steam_id.split(":")

        group = SteamID(steam_id_aux[2][:-1])

        steam_id_aux = group.as_steam2

        team = chat_info[2][:-1]

        log_send = f"**{name}** (#{player_id}) `{steam_id_aux}` <{team} {team_show}:  {log[1][:-1]}"

    return log_send



class ChatRelay(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.relay.start()


    @tasks.loop(seconds=0)
    async def relay(self):
        servers = await load_json('./json/servers.json')
        try:
            data = sock.recvfrom(4096)
        except socket.timeout as e:
            return
        chat = data[0].decode('utf-8', 'ignore')
        adr = data[1]
        print(f"Rec From {adr} -> {chat}")
        if '<[U:' in chat and chat.startswith('RL') and 'say' in chat:
            for server in servers:
                if server == f"{adr[0]}:{adr[1]}":
                    try:
                        channel_id = servers[server]["discord_channel_id"]
                        channel_id = self.client.get_channel(channel_id)
                        log = parselog(chat)
                        await channel_id.send(log)
                    except Exception as e:
                        print(f"Chat Relay Error: ({server}) | {e}")
                    break
        elif 'rcon from' in chat:
            for server in servers:
                if server == f"{adr[0]}:{adr[1]}":
                    channel_id = servers[server]["discord_channel_id"]
                    channel_id = self.client.get_channel(channel_id)
                    chat = chat[25:]
                    await channel_id.send(f"**`{chat[:-1]}`**")
                    break
        elif '<[U:' in chat and chat.startswith('RL') and 'disconnected' in chat:
            for server in servers:
                if server == f"{adr[0]}:{adr[1]}":
                    channel_id = servers[server]["discord_channel_id"]
                    channel_id = self.client.get_channel(channel_id)
                    chat = chat[25:]
                    await channel_id.send(f"`{chat[:-1]}`")
                    break
        elif '<[U:' in chat and chat.startswith('RL') and 'connected' in chat:
            for server in servers:
                if server == f"{adr[0]}:{adr[1]}":
                    channel_id = servers[server]["discord_channel_id"]
                    channel_id = self.client.get_channel(channel_id)
                    chat = chat[25:]
                    await channel_id.send(f"`{chat[:-1]}`")
                    break
        else:
            pass

def setup(client):
    client.add_cog(ChatRelay(client))
