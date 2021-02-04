
import discord
import json
import re
import valve.rcon
from discord.ext import commands
from jishaku.functools import executor_function
from valve.source.a2s import ServerQuerier
import valve.rcon
from steam.steamid import SteamID

valve.rcon.RCONMessage.ENCODING = "utf-8"

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
    #SERVER_PUBLIC_IP = CONFIG["ip"]
    #PORT = CONFIG["port"]
    PREFIX = CONFIG["command_prefix"]


def format_status_log(log):
    new_log = ' '.join([x for x in log.split(' ') if len(x)>0])

    split_log = new_log.split('"')

    second_split_log = split_log[2].split(" ")

    game_id = split_log[0]
    player_name = split_log[1]
    steamid = second_split_log[1]
    connected = second_split_log[2]
    ping = second_split_log[3]
    loss = second_split_log[4]
    state = second_split_log[5]
    ip = second_split_log[6]

    steam_id_aux = steamid.split(":")

    group = SteamID(steam_id_aux[2][:-1])

    steam_id_aux = group.as_steam2

    text = f'(#{game_id}) "{player_name}" `{steam_id_aux}` <{connected}> <{ping} ms> <{state}> `{ip}`'
    return text



class ChatRelay(commands.Cog):

    def __init__(self, client):
        self.client = client


    @commands.Cog.listener()
    async def on_message(self, message):
        #await self.client.process_commands(message)

        if message.content.startswith(PREFIX): # Ignore  commands
            return

        if message.author == self.client.user:      # Ignore bot
            return

        servers = await load_json('./json/servers.json')
        for server in servers:
            channel_id = servers[server]["discord_channel_id"]
            if message.channel.id == channel_id:
                author = message.author.name
                addr = server.split(":")
                addr = (addr[0], int(addr[1]))
                send_msg = f"sm_say {author} : {message.content}".encode("utf-8")
                rcon_password = servers[server]["rcon_password"]
                try:
                    valve.rcon.execute(addr, rcon_password, send_msg) # Send sm_say [msg] to console
                except:
                    pass # Stupid fix
                break

    @commands.command(aliases=['c'])
    async def cmd(self, ctx, *, cmd_):
        servers = await load_json('./json/servers.json')
        for server in servers:
            channel_id = servers[server]["discord_channel_id"]
            if ctx.channel.id == channel_id:
                addr = server.split(":")
                addr = (addr[0], int(addr[1]))
                rcon_password = servers[server]["rcon_password"]
                try:
                    """print("Here")
                    rcon = valve.rcon.RCON(addr, rcon_password, timeout=None)
                    print("Here2")
                    rcon.connect()
                    print("Her3")
                    rcon.authenticate()
                    print("Her4")
                    command = rcon.__call__(cmd_)
                    print("Her5")"""
                    rcon = valve.rcon.RCON(addr, rcon_password, timeout=None)
                    rcon.connect()
                    rcon.authenticate()
                    response = rcon.execute(cmd_)
                    response_text = response.body.decode("utf-8")
                    log1, log2 = "", ""
                    if cmd_ == 'status':
                        response_text = response_text.split("#")
                        for item in range(2, len(response_text)):
                            if item < len(response_text)/2:
                                add = format_status_log(response_text[item])
                                log1 = log1 + add + "\n"
                            else:
                                add = format_status_log(response_text[item])
                                log2 = log2 + add + "\n"
                        log1 = log1 + f"{chr(701)}"
                        await ctx.send(log1)
                        await ctx.send(log2)
                    else:
                        await ctx.send(f"***__{response_text}__***")
                except Exception as e:
                    print(f"Command Error: {e}")
                break

    @commands.command(aliases=['si', 'sinfo', 'serveri', 'info'])
    async def serverinfo(self, ctx):
        # Valve Module error a2a.py ping function -> monotoic and t_send !!!!!!!!!!!!!!!!!!
        servers = await load_json('./json/servers.json')
        for server in servers:
            channel_id = servers[server]["discord_channel_id"]
            if ctx.channel.id == channel_id:
                addr = server.split(":")
                addr = (addr[0], int(addr[1]))
                with ServerQuerier(addr) as server_queri:
                    server_info = server_queri.info()
                    ping = server_queri.ping()
                embed = discord.Embed(title = server_info["server_name"], description=server)
                embed.add_field(name='Game', value=server_info["game"], inline=False)
                embed.add_field(name='Map', value=server_info["map"], inline=False)
                embed.add_field(name='Players Online', value=server_info["player_count"] - server_info["bot_count"], inline=False)
                embed.add_field(name='Latency', value=f"{round(ping)} ms.", inline=False)
                embed.add_field(name='Bot Count', value=server_info["bot_count"], inline=False)
                embed.add_field(name='Vac Enabled', value=True if server_info["vac_enabled"] == 1 else False, inline=False)
                embed.add_field(name='Version', value=server_info["version"], inline=False)

                await ctx.send(embed=embed)
                break

def setup(client):
    client.add_cog(ChatRelay(client))