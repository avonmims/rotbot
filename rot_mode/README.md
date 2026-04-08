## Workflow:
1. add youtube link and custom name to **to_dl.csv**, seperated by comma of course
2. run **ingest.py** in terminal to "scrape" audio from youtube and place mp3 into folder
3. previously processed links will be skipped, new ones will be processed

## Purpose:
- **mp3_clips** is the "warehouse" our bot is sourcing to package files into a dataframe for simplified selection processes during **rot mode**

*for information on what **rot mode** is, see the [root directory](../README.md)*