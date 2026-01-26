import discord
import gspread
import yt_dlp
import random
import asyncio
import array
from oauth2client.service_account import ServiceAccountCredentials
from discord.ext import commands

# 1. set up discord bot
intents = discord.Intents.default()
intents.message_content = True  # enable access to message content
bot = commands.Bot(command_prefix='!', intents=intents)

# 2. set up google sheets access
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds) # authorize bot to access Google Sheets
sheet1 = client.open("youtube_links").worksheet("Occasional Sounds")  # open the Google Sheet for "Occasional Sounds"
sheet2 = client.open("youtube_links").worksheet("LQ Music") # open the Google Sheet for "LQ Music"

# 3. yt-dlp options (high-quality audio)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True, 'nocheck_certificate': True,
    'quiet': True, 'no_warnings': True, 'source_address': '0.0.0.0'
    }
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

# 4. custom audio source to mix multiple audio streams

class MultipleAudioSource(discord.AudioSource):
    def __init__(self):
        self.sources = []

    def add_source(self, source):
        self.sources.append(source)

    def is_opus(self):
        return False # we are using PCM audio

    def read(self):
        frame_size = 3840
        if not self.sources:
            return bytes([0] * frame_size) # silence if no sources
        
        data_s = []
        for source in self.sources[:]:
            data = source.read()
            if not data:
                self.sources.remove(source)
                continue

            if len(data) < frame_size:
                data += bytes([0] * (frame_size - len(data))) # pad with silence if too short
            data_s.append(data)

        if not data_s:
            return bytes([0] * frame_size) # silence if all sources ended
        
        arrays = [array.array('h', data) for data in data_s] # mix audio samples
        mixed = [0] * (frame_size // 2)
        for arr in arrays:
            for i in range(len(mixed)):
                mixed[i] += int(arr[i])

        for i in range(len(mixed)):
            if mixed[i] > 32767:
                mixed[i] = 32767
            elif mixed[i] < -32768:
                mixed[i] = -32768

        mixed_array = array.array('h', mixed)
        return mixed_array.tobytes()

# --------- bot commands ---------

@bot.event
async def on_ready(): 
    print(f'logged in as {bot.user.name} (ID: {bot.user.id})')
    print('big pp bot is ready to serve')
    print('------') # terminal initiation message

@bot.command()
async def hello(ctx): # hello command
    await ctx.send('what\'s up') # simple hello command

@bot.command() # join command
async def join(ctx):
    """Joins the voice channel of the user who invoked the command"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        try:
            if ctx.voice_client is not None: # check if bot is already in a voice channel
                if ctx.voice_client.channel == channel: # already in the same channel, do nothing
                    return False
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect()
            await ctx.send(f'joined {channel.name}')
            return True
        except Exception as e:
            print(f'error joining voice channel: {e}')
            await ctx.send(f'error joining voice channel: {e}')
            return False
    else:
        await ctx.send('you have to join a voice channel first dummy')
        return False

@bot.command() # leave command
async def leave(ctx):
    """Disconnects the bot from the voice channel and resets the mixer"""
    vc = ctx.voice_client
    if vc:
        if not ctx.author.voice or ctx.author.voice.channel != vc.channel: # check if user is in same channel
            return await ctx.send(f'you must be in the same voice channel to use the !leave command')
        if hasattr(vc, 'mixer'):
            vc.mixer = None  # reset mixer
        await vc.disconnect()
        await ctx.send('left the voice channel')
    else:
        await ctx.send('i am not in a voice channel')

@bot.command() # !random command for "Occasional Sounds" initiation
async def rot(ctx):
    """Picks 4-6 random links from the Google Sheet and plays them"""
    records = sheet1.get_all_records() # fetch all rows from the sheet
    count = random.randint(4, 6) # 4-6 random selections
    matches = random.sample(records, count) # randomly select a link

    await ctx.invoke(join)  # ensure bot is in voice channel

    for _ in range(10): # wait for connection to establish
        vc = ctx.voice_client
        if vc and vc.is_connected():
            break
        await asyncio.sleep(0.5)
    else:
        return await ctx.send('failed to connect to voice channel')
    
    #if hasattr(vc, 'mixer') and vc.mixer is not None and vc.is_playing(): # if already playing, return inform !shuffle
    #    return await ctx.send (f'audio playing... use !shuffle to re-roll selection')

    if vc.is_playing():
        vc.stop()  # stop current playback
    if hasattr(vc, 'mixer'):
        vc.mixer = None  # reset mixer
    
    vc.mixer = MultipleAudioSource()  # initialize mixer if not present
    vc.last_mode = 'rot' # track mode

    try:
        vc.play(vc.mixer)
    except Exception as e:
        print(f'handshake error: {e}')
        return await ctx.send(f'error starting audio playback: {e}')
        
    played_titles = []
    for match in matches:
        url = match['link']
        title = match['title']
        genre = match['genre']
        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl: # play the audio using yt-dlp
                info = ydl.extract_info(url, download=False)
                url2 = info['url']
            new_source = discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS) # add new sound to mixer
            vc.mixer.add_source(new_source)
            played_titles.append(f'**{title}** | genre: **{genre}**')
        except Exception as e:
            await ctx.send(f'error adding source {title}: {str(e)}')

    await ctx.send(f'playing:\n' + '\n'.join(played_titles))

@bot.command() # !shuffle command for "Occasional Sounds"
async def skip(ctx):
    """Stops current playback and re-rolls selection, displaying new titles"""
    vc = ctx.voice_client
    if not vc or not vc.is_connected():
        return await ctx.send('i am not in a voice channel') # return warning if not connected

    if vc.is_playing():
        vc.stop()  # stop current playback
    if hasattr(vc, 'mixer'):
        vc.mixer = None  # reset mixer

    mode = getattr(vc, 'last_mode', None)
    if mode == 'rot':
        records = sheet1.get_all_records() # fetch new selections
        count = random.randint(4, 6)
        matches = random.sample(records, count)
        vc.mixer = MultipleAudioSource()  # initialize new mixer
        try:
            vc.play(vc.mixer)
        except Exception as e:
            print(f'handshake error: {e}')
            return await ctx.send(f'error starting audio playback: {e}')
        played_titles = []
        for match in matches:
            url = match['link']
            title = match['title']
            genre = match['genre']
            try:
                with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(url, download=False)
                    url2 = info['url']
                new_source = discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS)
                vc.mixer.add_source(new_source)
                played_titles.append(f'**{title}** | genre: **{genre}**')
            except Exception as e:
                await ctx.send(f'error adding source {title}: {str(e)}')
        await ctx.send(f'playing:\n' + '\n'.join(played_titles))
    elif mode == 'song':
        records = sheet2.get_all_records() # fetch all rows
        match = random.choice(records) # randomly select link
        url = match['link']
        title = match['title']
        genre = match['genre']
        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                url2 = info['url']
            source = discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS)
            vc.play(source)
            await ctx.send(f'now playing: **{title}** | genre: **{genre}**')
        except Exception as e:
            await ctx.send(f'error playing song {title}: {str(e)}')
    else:
        await ctx.send('no previous mode found, use !rot or !song first')

@bot.command() # !song command for "LQ Music"
async def song(ctx):
    """Plays a random song from the LQ Music Google Sheet"""
    records = sheet2.get_all_records() # fetch all rows from the sheet
    match = random.choice(records) # randomly select a link

    await ctx.invoke(join)  # ensure bot is in voice channel

    for _ in range(10): # wait for connection to establish
        vc = ctx.voice_client
        if vc and vc.is_connected():
            break
        await asyncio.sleep(0.5)
    else:
        return await ctx.send('failed to connect to voice channel')
    
    if vc.is_playing():
        vc.stop()  # stop current playback
    if hasattr(vc, 'mixer'):
        vc.mixer = None  # reset mixer
    
    vc.last_mode = 'song' # track mode
    
    url = match['link']
    title = match['title']
    genre = match['genre']
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl: # play the audio using yt-dlp
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
        source = discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS)
        vc.play(source)
        await ctx.send(f'now playing: **{title}** | genre: **{genre}**')
    except Exception as e:
        await ctx.send(f'error playing song {title}: {str(e)}')


bot.run('MTQ2MzY2MjYxNjQ3MDYxODI1Mw.Gurfed.LWTRFHLtC6pVseIlB-v7yArSIhpoIjpS3zZFQ4')

# check notion for updated to-do list
# check notion for notes... lol