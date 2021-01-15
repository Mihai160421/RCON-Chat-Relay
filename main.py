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
    TOKEN = CONFIG["token"]
    PREFIX = CONFIG["command_prefix"]


SERVER_LOCAL_IP = socket.gethostbyname(socket.gethostname()) # Get local ip

ADDR = (SERVER_LOCAL_IP, PORT)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(ADDR)
sock.settimeout(0.001) # Recv Timeout

intents = discord.Intents.default()
intents.members=True
client = commands.Bot(command_prefix='>', intents=intents)


@client.event
async def on_ready():
    print(f"{client.user.name} ready!")
    relay.start()

@client.event
async def on_message(message):
    await client.process_commands(message)

    if message.content.startswith(PREFIX): # Ignore  commands
        return

    if message.author == client.user:      # Ignore bot
        return

    servers = await load_json('./json/servers.json')
    for server in servers:
        channel_id = servers[server]["discord_channel_id"]
        if message.channel.id == channel_id:
            addr = server.split(":")
            addr = (addr[0], int(addr[1]))
            rcon_password = servers[server]["rcon_password"]
            valve.rcon.execute(addr, rcon_password, f"say {message.content}") # Send sm_say [msg] to console
            break

@client.command()
async def cmd(ctx, *, cmd_):
    servers = await load_json('./json/servers.json')
    for server in servers:
        channel_id = servers[server]["discord_channel_id"]
        if ctx.channel.id == channel_id:
            addr = server.split(":")
            addr = (addr[0], int(addr[1]))
            rcon_password = servers[server]["rcon_password"]
            try:
                rcon = valve.rcon.RCON(addr, rcon_password, timeout=None)
                rcon.connect()
                rcon.authenticate()
                command = rcon.__call__(cmd_)
                await ctx.send(f"***__{command}__***")
            except Exception as e:
                print(f"Command Error: {e}")
            break

@client.command(aliases=['si', 'sinfo', 'serveri', 'info'])
async def serverinfo(ctx):
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
            embed.add_field(name='Players Online', value=server_info["player_count"], inline=False)
            embed.add_field(name='Latency', value=f"{round(ping)} ms.", inline=False)
            embed.add_field(name='Bot Count', value=server_info["bot_count"], inline=False)
            embed.add_field(name='Vac Enabled', value=True if server_info["vac_enabled"] == 1 else False, inline=False)
            embed.add_field(name='Version', value=server_info["version"], inline=False)

            await ctx.send(embed=embed)
            break

@client.command()
@commands.has_permissions(administrator=True) # Administrator permission required (user)
async def addserver(ctx, addr='', rcon_password=''): # Add server to servers.json
    if addr == '':
        await ctx.send("You need an ip")
        return
    if rcon_password == '':
        await ctx.send("Rcon password?")
        return

    channel_id = ctx.channel.id

    await ctx.message.delete()
    server = {"discord_channel_id": channel_id, f"rcon_password": rcon_password}


    servers = await load_json('./json/servers.json')

    servers[addr] = server

    await dump_json('./json/servers.json', servers)

    await ctx.send(f"**`{addr}`** Added!")

    addr = addr.split(":")
    addr = (addr[0], int(addr[1]))
    cmd = f'logaddress_add "{SERVER_PUBLIC_IP}:{PORT}"'
    valve.rcon.execute(addr, rcon_password, cmd)
    valve.rcon.execute(addr, rcon_password, "log on")

def parselog(log):
    if 'say_team' in log:
        log = log[27:].split(" say_team ")
    else:
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

        log_send = f"**{name}** (#{player_id}) `{steam_id_aux}` <{team} :  {log[1][:-1]}"

    return log_send


@tasks.loop(seconds=0)
async def relay():
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
                    channel_id = client.get_channel(channel_id)
                    log = parselog(chat)
                    await channel_id.send(log)
                except Exception as e:
                    print(f"Chat Relay Error: ({server}) | {e}")
                break
    elif '<Console><Console>' in chat:
        for server in servers:
            if server == f"{adr[0]}:{adr[1]}":
                channel_id = servers[server]["discord_channel_id"]
                channel_id = client.get_channel(channel_id)
                chat = chat[46:].replace('"', "")
                await channel_id.send(f"**`{chat[:-1]}`**")
                break
    elif '<[U:' in chat and chat.startswith('RL') and 'disconnected' in chat:
        for server in servers:
            if server == f"{adr[0]}:{adr[1]}":
                channel_id = servers[server]["discord_channel_id"]
                channel_id = client.get_channel(channel_id)
                chat = chat[25:]
                await channel_id.send(f"`{chat[:-1]}`")
                break
    elif '<[U:' in chat and chat.startswith('RL') and 'connected' in chat:
        for server in servers:
            if server == f"{adr[0]}:{adr[1]}":
                channel_id = servers[server]["discord_channel_id"]
                channel_id = client.get_channel(channel_id)
                chat = chat[25:]
                await channel_id.send(f"`{chat[:-1]}`")
                break
    else:
        pass


client.run(TOKEN)

