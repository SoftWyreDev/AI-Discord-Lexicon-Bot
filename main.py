import discord
from discord import app_commands
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import requests
from datetime import datetime, timedelta

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

LM_STUDIO_URL = os.getenv("LM_STUDIO_URL")

pre_prompt = ""

# Stores the last time each user triggered a command
last_command_time = {}

# Cooldown period (seconds between allowed commands)
COOLDOWN_TIME = 15 

def load_pre_prompt():
    global pre_prompt
    with open("preprompt.txt", "r", encoding="utf-8") as f:
        pre_prompt = f.read()


def get_ai_response(prompt):
    try:
        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "model": "mistral-7b-instruct-v0.3",  
            "messages": [
                {"role": "user", "content": f"{pre_prompt} {prompt}"}
            ],
            "temperature": 1.0
        }

        response = requests.post(
            f"{LM_STUDIO_URL}/v1/chat/completions",
            headers=headers,
            json=payload
        )

        print(f"DEBUG: {response.status_code} - {response.text}")

        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            if "</think>" in content:
                return content.split("</think>")[-1].strip()
            else:
                return content.strip()
        else:
            return f"Error: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"

GUILD_ID = int(os.getenv("GUILD_ID"))  
    
@bot.event
async def on_ready():
    load_pre_prompt()
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    # Use your actual server ID for syncing commands (optional)
    # guild = discord.Object(id=GUILD_ID) 
    # await bot.tree.sync(guild=guild)
    # print(f"Commands synced to {guild.id}")


async def check_cooldown(interaction: discord.Interaction) -> bool:
    user_id = interaction.user.id
    current_time = datetime.now()

    if user_id in last_command_time:
        time_diff = current_time - last_command_time[user_id]
        if time_diff < timedelta(seconds=COOLDOWN_TIME):
            remaining_time = COOLDOWN_TIME - time_diff.total_seconds()
            await interaction.response.send_message(f"Please wait {remaining_time:.1f} seconds before using the command again :)", ephemeral=True)
            return False

    # Update the last command time for the user
    last_command_time[user_id] = current_time
    return True

async def full_response(interaction, command_name, prompt, response):
    max_len = 1900
    header = f"**/{command_name} {prompt}**\n\n" if prompt else f"**/{command_name}**\n\n"
    # Send header first
    await interaction.followup.send(header)
    # Split response into chunks
    while len(response) > max_len:
        chunk = response[:max_len]
        await interaction.followup.send(chunk)
        response = response[max_len:]
    if response:
        await interaction.followup.send(response)


@bot.tree.command(name="lexicon", description="Responds to the prompt using the tone of your custom lexicon.")
@app_commands.describe(prompt="Any purpose prompt to ask or instruct Lexicon Bot however you like.")
async def lexicon_command(interaction: discord.Interaction, prompt: str):
    if not await check_cooldown(interaction):
        return

    await interaction.response.defer()  
    ai_response = get_ai_response(prompt)
    await full_response(interaction, "lexicon", prompt, ai_response)


@bot.tree.command(name="ltranslate", description="Attempt to translate the prompt into custom lexicon speak.")
@app_commands.describe(prompt="A phrase you want to get translated using a custom lexicon.")
async def ltranslate_command(interaction: discord.Interaction, prompt: str):
    if not await check_cooldown(interaction):
        return

    await interaction.response.defer()
    ai_prompt = f"""
    You are a translation bot that converts normal English into funny, bizarre slang using the custom lexicon style. Guidelines: Respond in a tone that’s wild, humorous, and chaotic.
    Use it as a thesaurus and be very creative. Don't go overboard on the words, use plenty of normal English words too.
    Respond with the translated sentence using the custom terms. Try to change lots of words, but still make it make sense and be related to their message.
    Do not include explanations, thoughts, or translation notes — just give the final translated sentence. Make the translation very similar length to their message.
    Input: {prompt}
    """
    ai_response = get_ai_response(ai_prompt)
    await full_response(interaction, "ltranslate", prompt, ai_response)


@bot.tree.command(name="newword", description="Invent a new custom lexicon word, give a definition, and an example.")
async def newword_command(interaction: discord.Interaction):
    if not await check_cooldown(interaction):
        return

    await interaction.response.defer()
    prompt = "Invent a bizarre or humorous new custom lexicon word. Provide:\n1. The word\n2. A sentence using it\n3. A funny or imaginative definition. Use a custom lexicon tone."
    ai_response = get_ai_response(prompt)
    await interaction.followup.send(ai_response)


@bot.tree.command(name="fortune", description="Reveal your strange, possibly dangerous future.")
async def fortune_command(interaction: discord.Interaction):
    if not await check_cooldown(interaction):
        return

    await interaction.response.defer()
    prompt = "Give me a cursed and bizarre fortune, or a wondrous epic fortune in the style of the custom lexicon. Make it a 50 percent chance to be good or bad. For example, 'You will find cheese in your shoe. Do not question fate.' Make it very short and weird."
    ai_response = get_ai_response(prompt)
    await interaction.followup.send(ai_response)


@bot.tree.command(name="rapbattle", description="Freestyle roast your opponent with custom lexicon diss bars.")
@app_commands.describe(opponent="A Discord member you would like to diss.")
async def rapbattle_command(interaction: discord.Interaction, opponent: discord.Member):
    if not await check_cooldown(interaction):
        return

    await interaction.response.defer()
    opponent_name = opponent.mention
    prompt = f"Write just a few freestyle rap battle lines dissing {opponent_name} in a playful, funny style. Make it short. Make sure to mention {opponent_name} in the rap."
    ai_response = get_ai_response(prompt)
    await full_response(interaction, "rapbattle", opponent_name, ai_response)


@bot.tree.command(name="ladvice", description="Receive cursed, unhelpful life advice.")
@app_commands.describe(topic="Anything you would like advice on.")
async def ladvice_command(interaction: discord.Interaction, topic: str = None):
    if not await check_cooldown(interaction):
        return

    await interaction.response.defer()
    if topic:
        prompt = f"Give some funny advice about: {topic}. Be humorous, unpredictable, and cursed. MUST be less than 2000 characters"
        display_prompt = f"ladvice {topic}"
    else:
        prompt = "Give some general funny life advice. Be humorous, unpredictable, and cursed. MUST be less than 2000 characters"
        display_prompt = "ladvice"
    ai_response = get_ai_response(prompt)
    await full_response(interaction, display_prompt, "", ai_response)


@bot.tree.command(name="summon", description="Generate a bizarre fantasy character with a chaotic backstory.")
async def summon_command(interaction: discord.Interaction):
    if not await check_cooldown(interaction):
        return

    await interaction.response.defer()
    prompt = "Create a ridiculous Dungeons & Dragons-style fantasy character with a weird class and backstory. Use humor, unexpected words, and chaotic energy. MUST be less than 2000 characters."
    ai_response = get_ai_response(prompt)
    await full_response(interaction, "summon", "", ai_response)


@bot.tree.command(name="pickup", description="Drop a funny, chaotic, or absurd pickup line.")
@app_commands.describe(user="A Discord member that you would like to hit on.")
async def pickup_command(interaction: discord.Interaction, user: discord.Member = None):
    if not await check_cooldown(interaction):
        return

    await interaction.response.defer()
    if user:
        target_name = user.mention
    else:
        target_name = "@someone"
    prompt = f"Give a funny, chaotic, or absurd pickup line directed at {target_name}. Mention {target_name} in the pickup line. Be creative, humorous, and maybe a little unhinged. MUST be less than 2000 characters"
    ai_response = get_ai_response(prompt)
    await full_response(interaction, "pickup", target_name, ai_response)


@bot.tree.command(name="mutate", description="Mutate any object into something cursed and insane.")
@app_commands.describe(object_to_mutate="Any object you would like to transform into something cursed and insane.")
async def mutate_command(interaction: discord.Interaction, object_to_mutate: str):
    if not await check_cooldown(interaction):
        return

    await interaction.response.defer()
    prompt = f"Mutate this object into something insane, bizarre, or cursed in a custom lexicon tone: {object_to_mutate}. Be extremely creative and unexpected. MUST be less than 2000 characters"
    ai_response = get_ai_response(prompt)
    await full_response(interaction, "mutate", object_to_mutate, ai_response)


@bot.tree.command(name="obituary", description="Generate a ridiculous legendary demise scenario.")
@app_commands.describe(user="A Discord member.", name="Name of a person")
async def obituary_command(interaction: discord.Interaction, user: discord.Member = None, name: str = None):
    if not await check_cooldown(interaction):
        return

    await interaction.response.defer()
    if user:
        target_name = user.mention
        display = f"obituary {user.display_name}"
    elif name:
        target_name = name
        display = f"obituary {name}"
    else:
        await interaction.followup.send("Please mention a user or type a name after /obituary.", ephemeral=True)
        return
    prompt = f"Write a ridiculous and hilarious legendary demise scenario for {target_name}. Keep it bizarre, over-the-top, and funny. MUST be less than 2000 characters"
    ai_response = get_ai_response(prompt)
    await full_response(interaction, display, "", ai_response)


@bot.tree.command(name="lhelp", description="Display a list of available commands.")
async def help_command(interaction: discord.Interaction):
    help_text = """
    **🛠 Available Commands:**

    🧠 `/lexicon [prompt]` – Respond to the prompt using the custom lexicon.

    📜 `/ltranslate [prompt]` – Attempt to translate the prompt into custom lexicon speak.

    🪄 `/newword` – Invent a new custom lexicon word, give a definition, and an example.

    🎤 `/rapbattle @user` – Freestyle roast your opponent with custom lexicon diss bars.

    💌 `/pickup @user` – Drop a funny, chaotic, or absurd pickup line.

    ☠️ `/obituary @user` or `/obituary [name]` – Generate a legendary demise scenario.

    🧬 `/mutate [object]` – Mutate any object into something cursed and insane.

    🧙 `/summon` – Generate a bizarre fantasy character with a chaotic backstory.

    🧻 `/ladvice` or `/ladvice [prompt]` – Receive funny, unhelpful life advice.

    🔮 `/fortune` – Reveal your strange, possibly dangerous future.

    ❓ `/lhelp` – Display this list of commands.

    Type any of these commands to unleash the chaos.
    """
    await interaction.response.send_message(help_text, ephemeral=True)


bot.run(token, log_handler=handler, log_level=logging.DEBUG)