import pandas as pd
import pathlib
import yt_dlp

base_path = pathlib.Path(__file__).parent / 'mp3_clips' # path to mp3 clips folder

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

queue_df = pd.read_csv(pathlib.Path(__file__).parent / 'to_dl.csv') # csv to df, url and name columns

queue_df['exists'] = queue_df['name'].apply(lambda x: (base_path / f'{x}.mp3').exists()) # check if file already exists, add to df
to_process = queue_df[queue_df['exists'] == False] # filter df to only ones that dont exist

# -- iterate through df and download each url as mp3 with yt_dlp, save as name.mp3 in mp3_clips folder
for _, row in to_process.iterrows():
    url = row['url']
    name = row['name']

    current_opts = ydl_opts.copy()
    current_opts['outtmpl'] = str(base_path / f'{name}.%(ext)s')
    
    with yt_dlp.YoutubeDL(current_opts) as ydl:
        ydl.download([url])