import random

import discord
from keep_alive import keep_alive
from discord.ext import commands
import os
import requests
from PIL import Image
from io import BytesIO
import time

token = os.environ['TOKEN']
client = commands.Bot(command_prefix='pls ', intents=discord.Intents.all())
encounter_animation_url = "https://media.tenor.com/t2CLuddXnz0AAAAC/pokemon-pokemon-encounter.gif"
encounters = dict()


def get_pokemon(id):
    response = requests.get(f'https://pokeapi.co/api/v2/pokemon/{id}/')

    if response.status_code == 200:
        data = response.json()
        print(data['name'])
        return data

    else:
        print('error' + response.status_code)


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


@client.event
async def on_ready():
    print('BOT is ready')
    for intent in discord.Intents.all():
        print(str(intent))


@client.event
async def on_reaction_add(reaction, user):
    if not user.bot:
        if reaction.message in encounters:
            capture_rate, attempts = encounters[reaction.message]
            if user not in attempts:
                attempts.add(user)
                roll = random.randint(0, 255)
                if roll < capture_rate:

                    await reaction.message.reply(f"{user.name} caught pokemon")
                    await reaction.remove(user)
                    encounters.pop(reaction.message)
                else:
                    await reaction.message.reply(f"you are so unlucky {roll}")

            else:
                await reaction.message.reply("you already tried to catch this pokemon")

        #else:
        #    await reaction.message.reply(":turtle: too late, be quicker next time :turtle:")


@client.command(aliases=["enc"])
async def encounter(ctx, message=""):
    id = random.randint(1, 1009)
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

        encounters[message] = (capture_rate, set())

    else:
        await ctx.send('unknown pokemon ' + message)


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


# @client.event
# async def on_message(message):
#    emoji = '\N{THUMBS UP SIGN}'
#    await message.add_reaction(emoji)
#    await client.process_commands(message)

def wtf(item):
    print(type(item), item, dir(item))


keep_alive()
client.run(token)
