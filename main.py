import json
import random

import discord
import pymongo

from keep_alive import keep_alive
from discord.ext import commands
import os
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
import time

token = os.environ['TOKEN']
db_user = os.environ['MONGO_USER']
db_password = os.environ['MONGO_PASS']
db_connection = f"mongodb+srv://{db_user}:{db_password}@cluster0.hterriy.mongodb.net/?retryWrites=true&w=majority"
db_client = pymongo.MongoClient(db_connection)
print("db info: " + str(db_client.server_info()))
db = db_client.get_database("pokemon")
client = commands.Bot(command_prefix='pls ', intents=discord.Intents.all(), activity=discord.Game('wit pokemon'))
encounter_animation_url = "https://media.tenor.com/t2CLuddXnz0AAAAC/pokemon-pokemon-encounter.gif"
encounters = dict()
current_habitat = dict()


def get_pokemon(id):
    response = requests.get(f'https://pokeapi.co/api/v2/pokemon/{id}/')

    if response.status_code == 200:
        data = response.json()
        print(data['name'])
        return data

    else:
        print('error' + str(response.status_code))


def bot_status(status):
    client = commands.Bot(command_prefix='pls ', intents=discord.Intents.all(), activity=discord.Game(status))


def get_species(url):
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        result = [index['flavor_text'] for index in data['flavor_text_entries'] if index['language']['name'] == 'en']
        return result[0]

    else:
        print('error' + response.status_code)


def get_capture_rate(url):
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        return data['capture_rate']

    else:
        print('error' + response.status_code)


@client.command(name='time')
async def send_time(ctx):
    current_time = datetime.now().strftime(r"%I:%M %p")
    await ctx.send(f'The current time is {current_time}')


@client.event
async def on_ready():
    print('BOT is ready')
    for intent in discord.Intents.all():
        print(str(intent))
    random_habitat()


@client.event
async def on_reaction_add(reaction, user):
    if not user.bot:
        if reaction.message in encounters:
            capture_rate, attempts, id = encounters[reaction.message]
            if user not in attempts:
                attempts.add(user)
                roll = random.randint(0, 255)
                if roll < capture_rate:

                    await reaction.message.reply(f"{user.name} caught pokemon")
                    await reaction.remove(user)
                    encounters.pop(reaction.message)
                    player_collection().update_one({"discord_id": user.id}, {"$push": {"owned_pokemon": id}})


                else:
                    await reaction.message.reply(f"you are so unlucky {roll}")

            else:
                await reaction.message.reply("you already tried to catch this pokemon")

        # else:
        #    await reaction.message.reply(":turtle: too late, be quicker next time :turtle:")


@client.command()
async def give(ctx, user: discord.Member, pokemon: str):
    if pokemon.isnumeric():
        id = int(pokemon)
        if player_collection().find_one({"discord_id": user.id})['owned_pokemon'].count(id) > 0:
            await ctx.send(f"{user.name} already has this pokemon")
        else:
            player_collection().update_one({"discord_id": user.id}, {"$push": {"owned_pokemon": id}})
            await ctx.send(f"{user.name} gave {pokemon} to {user.name}")


@client.command(aliases=["trade"])
async def trade_command(ctx, user: discord.Member, *message):
    trade = {
        'guildId': ctx.guild.id,
        'messageId': ctx.message.id,
        'offers': {
            str(ctx.author.id): message,
            str(user.id): [],
        },
        'closed': False
    }
    save_trade(ctx.message.id, trade)
    embed = await trade_embed(trade)
    await ctx.send(embed=embed)


async def trade_embed(trade):
    users = [await client.fetch_user(id) for id in trade['offers'].keys()]
    embed = discord.Embed(title="TRADE", description=f"{users[0].mention} and {users[1].mention}", color=0x8831a0)
    for user in users:
        embed.add_field(name=f"{user.display_name} offers:", value="", inline=False)
        for id in trade['offers'][str(user.id)]:
            embed.add_field(name=get_pokemon(id)['name'], value=get_emoji(id), inline=True)
    embed.set_footer(text="reply to this message")
    return embed


@client.command(aliases=["enc"])
async def encounter(ctx, message=""):
    species = random.choice(current_habitat['pokemon_species'])
    url = species["url"]
    id = url[42:-1]
    print(id)
    data = get_pokemon(id)
    if data:

        # assume 'image_url' is the URL of the image you want to add to the embed
        response = requests.get(data['sprites']['front_default'])
        image = Image.open(BytesIO(response.content))

        # resize the image to the desired size
        image = image.resize((1024, 1024))

        # create a Discord file object from the resized image
        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            file = discord.File(fp=image_binary, filename='image.png')

        # create the embed and add the image + name
        embed = discord.Embed(title=data["name"].capitalize())
        embed.set_image(url='attachment://image.png')

        capture_rate = get_capture_rate(data['species']['url'])
        embed.add_field(name='capture_rate', value=capture_rate)
        embed.set_footer(text=data['id'])
        message = await ctx.send(encounter_animation_url)
        time.sleep(2)
        await message.edit(content=None, attachments=[file], embed=embed)

        await message.add_reaction(":pokeball:1118548894419275977")

        encounters[message] = (capture_rate, set(), int(id))

    else:
        await ctx.send('unknown pokemon ' + message)


@client.command(aliases=['h'])
async def habitat(ctx, message=""):
    global current_habitat, client
    random_habitat()
    await ctx.send(current_habitat["name"])
    print(current_habitat)
    await client.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=current_habitat["name"]))


def random_habitat():
    global current_habitat
    response = requests.get(f"https://pokeapi.co/api/v2/pokemon-habitat/{random.randint(1, 9)}/")
    current_habitat = json.loads(response.text)


@client.command(help='Shows information about the specified pokemon.', aliases=['p'])
async def pokemon(ctx, message=''):
    wtf(message)
    data = get_pokemon(message)

    if data:
        species = get_species(data['species']['url'])

        embed = discord.Embed(title=data["name"].capitalize(),
                              url="https://assets.pokemon.com/assets/cms2/img/pokedex/full/001.png",
                              description=species.replace('\n', ' '),
                              color=0x27b030)
        # embed.set_thumbnail(url="https://assets.pokemon.com/assets/cms2/img/pokedex/full/001.png")
        embed.add_field(name="Height", value=data['height'], inline=True)
        embed.add_field(name="Weight", value=data['weight'], inline=True)

        names = [index['type']['name'] for index in data['types']]

        embed.add_field(name="Types", value=', '.join(names), inline=False)

        names = {index['ability']['name'] for index in data['abilities']}

        embed.add_field(name="Abilities", value=', '.join(names), inline=False)

        species = get_species(data['species']['url'])
        print(species)

        # names = list()
        # for index in data['moves']:
        #     names.append(index['move']['name'])
        # embed.add_field(name="Moves", value=', '.join(names), inline=False)

        embed.set_thumbnail(url=(data['sprites']['front_default']))

        # positive = [number for number in range(-10, 10) if number > 0]

        positive = list()
        for number in range(-10, 10):
            if number > 0:
                positive.append(number)
        print(positive)  # [1, 2, 3, 4, 5, 6, 7, 8, 9]

        embed.set_footer(text=data['id'])
        await ctx.send(embed=embed)



    else:
        await ctx.send('unknown pokemon ' + message)


@client.command(aliases=['i'])
async def inventory(ctx, message=''):
    player = player_collection().find_one({"discord_id": ctx.author.id})
    result = list()
    for id in sorted(player["owned_pokemon"]):
        result.append(f'`{str(id).rjust(4)}` {get_emoji(id)} {get_pokemon(id)["name"].title()}')

    if player:
        await ctx.reply("\n".join(result))



    else:
        await ctx.reply("not registered :cry:")


def get_trade(message_id):
    return db.get_collection("trades").find_one({"message_id": message_id})


def save_trade(message_id, trade):
    db.get_collection("trades").update_one({"message_id": message_id}, {"$set": trade}, upsert=True)


def player_collection():
    return db.get_collection("player")


def get_emoji(id):
    emoji = db.get_collection("emojis").find_one({"pokemon_id": int(id)})
    return emoji["emoji"] if emoji else ":interrobang:"


@client.command()
async def register(ctx, message=''):
    wtf(message)
    data = {
        "discord_id": ctx.author.id,
        "owned_pokemon": [1, 6, 19]
    }
    player_collection().update_one({"discord_id": ctx.author.id}, {"$set": data}, upsert=True)

    await ctx.send('you are registered🥳')


# @client.command()
# async def emotes(ctx, message=None):
@client.event
async def on_guild_join(guild):
    if not guild.name.startswith("pokemonemote"):
        print(f"joined server {guild.name}, not generated emojis")
    name, min, max = guild.name.split()

    for id in range(int(min), int(max) + 1):
        data = get_pokemon(id)
        if data:
            print(id, data["name"])
            # assume 'image_url' is the URL of the image you want to add to the embed
            response = requests.get(data['sprites']['front_default'])
            image = Image.open(BytesIO(response.content))

            # resize the image to the desired size
            image = image.crop(image.getbbox())
            image = image.resize((1024, 1024))
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                await guild.create_custom_emoji(name=f"pokemon_{id}", image=image_binary.getvalue())


@client.command()
async def register_emojis(ctx):
    collection = db.get_collection("emojis")
    for guild in client.guilds:
        print(guild.name)
        for emoji in guild.emojis:
            if emoji.name.startswith("pokemon_"):
                id = int(emoji.name.split("_")[1])
                data = {
                    "pokemon_id": id,
                    "emoji": f'<:pokemon_{id}:{emoji.id}>'
                }
                collection.update_one({"pokemon_id": id}, {"$set": data}, upsert=True)


@client.event
async def on_message(message):
    if message.reference is not None:
        trade = get_trade(message.reference.message_id)
        if trade:
            if message.author.id in trade['offers']:
                for pokemon_id in message.content.split():
                    trade['offers'][message.author.id].append(pokemon_id)
                save_trade(message.id,trade)
                embed=trade_embed(trade)
                await client.fetch_channel(message.reference.channel_id).fetch_message(message.reference.message_id).edit(embed=embed)


    await client.process_commands(message)


def wtf(item):
    print(type(item), item, dir(item))


keep_alive()
client.run(token)
