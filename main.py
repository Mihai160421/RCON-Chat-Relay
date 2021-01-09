import socket
import discord
import json
import valve.rcon
from discord.ext import commands, tasks
from jishaku.functools import executor_function

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


intents = discord.Intents.default()
intents.members=True
client = commands.Bot(command_prefix=PREFIX, intents=intents)



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
                command = valve.rcon.execute(addr, rcon_password, cmd_)
                await ctx.send(f"***__{command}__***")
            except:
                pass

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


@tasks.loop(seconds=0)
async def relay():
    servers = await load_json('./json/servers.json')
    data = sock.recvfrom(4096)
    chat = data[0].decode('utf-8', 'ignore')
    adr = data[1]
    if '<[U:' in chat and chat.startswith('RL') and 'say' in chat:
        for server in servers:
            if server == f"{adr[0]}:{adr[1]}":
                channel_id = servers[server]["discord_channel_id"]
                channel_id = client.get_channel(channel_id)
                chat = chat[25:].replace(">", "").split("<")
                name = chat[0].replace('"', "")
                msg = chat[3].split("say")
                msg = msg[1].replace('"', "")
                log = f"**{name}** (#{chat[1]}) `{chat[2]}` : {msg}"
                await channel_id.send(log[:-1])
    elif '<Console><Console>' in chat:
        for server in servers:
            if server == f"{adr[0]}:{adr[1]}":
                channel_id = servers[server]["discord_channel_id"]
                channel_id = client.get_channel(channel_id)
                chat = chat[46:].replace('"', "")
                await channel_id.send(f"**`{chat[:-1]}`**")
    elif '<[U:' in chat and chat.startswith('RL') and 'disconnected' in chat:
        for server in servers:
            if server == f"{adr[0]}:{adr[1]}":
                channel_id = servers[server]["discord_channel_id"]
                channel_id = client.get_channel(channel_id)
                chat = chat[25:]
                await channel_id.send(f"`{chat[:-1]}`")
    elif '<[U:' in chat and chat.startswith('RL') and 'connected' in chat:
        for server in servers:
            if server == f"{adr[0]}:{adr[1]}":
                channel_id = servers[server]["discord_channel_id"]
                channel_id = client.get_channel(channel_id)
                chat = chat[25:]
                await channel_id.send(f"`{chat[:-1]}`")
client.run(TOKEN)

