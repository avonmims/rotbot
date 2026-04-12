import os
import random
import pathlib
from dotenv import load_dotenv
from discord.ext import commands

# -- load bot token from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# -- establish mp3_clips directory path
clips_dir = pathlib.Path(__file__).parent / 'mp3_clips'

# -- hell yea new beningings lol, above line is for loading super secret bot token