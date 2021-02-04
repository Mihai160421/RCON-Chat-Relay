import socket
import discord
import os
import json
from discord.ext import commands
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

intents = discord.Intents.default()
intents.members=True
client = commands.Bot(command_prefix='>', intents=intents)


@client.event
async def on_ready():
    print(f"{client.user.name} ready!")


@client.command()
@commands.has_permissions(administrator=True)
async def load(ctx, extension):
    try:
        client.load_extension(f"cogs.{extension}")
        await ctx.send(f"{extension} loaded.")
    except Exception as e:
        print(e)


@client.command()
@commands.has_permissions(administrator=True)
async def unload(ctx, extension):
    try:
        client.unload_extension(f"cogs.{extension}")
        await ctx.send(f"{extension} unloaded.")
    except Exception as e:
        print(e)

@client.command()
@commands.has_permissions(administrator=True)
async def reload(ctx, extension):
    try:
        client.unload_extension(f"cogs.{extension}")
        client.load_extension(f"cogs.{extension}")
        await ctx.send(f"{extension} reloaded.")
    except Exception as e:
        print(e)

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')
        print(f"{filename} loaded.")


client.run(TOKEN)

