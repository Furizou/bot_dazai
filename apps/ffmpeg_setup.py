# # shared.py
# voice_client_dict = {}
# yt_dl_options = {"format": "bestaudio/best"}
# ytdl = None  # Will be initialized in main.py
# ffmpeg_options = {'options': '-vn'}

import yt_dlp

yt_dl_options = {"format": "bestaudio/best"}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)
voice_client_dict = {}
ffmpeg_options = {'options': '-vn'}

music_queue = {}  # Dictionary to store queues for each guild
timeout_timers = {}  # Dictionary to store timers for each voice channel