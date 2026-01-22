import discord
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True  # enable access to message content

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds) # authorize bot to access Google Sheets

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'logged in as {bot.user.name} (ID: {bot.user.id})')
    print('big pp bot is ready to serve')
    print('------') # terminal initiation message

@bot.command()
async def hello(ctx):
    await ctx.send('what\'s up') # simple hello command

@bot.command()
async def check_links(ctx):
    sheet = client.open("youtube_links").sheet1 # open sheet
    data = sheet.get_all_records() # get all records
    first_link = data[0]['link']
    await ctx.send(f'i found the first link: {first_link}') # send first link found in sheet

bot.run('MTQ2MzY2MjYxNjQ3MDYxODI1Mw.Gurfed.LWTRFHLtC6pVseIlB-v7yArSIhpoIjpS3zZFQ4')