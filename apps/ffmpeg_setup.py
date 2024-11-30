# # shared.py
# voice_client_dict = {}
# yt_dl_options = {"format": "bestaudio/best"}
# ytdl = None  # Will be initialized in main.py
# ffmpeg_options = {'options': '-vn'}

import yt_dlp

# yt_dl_options = {"format": "bestaudio/best"}
# In ffmpeg_setup.py
yt_dl_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # Bind to IPv4 since IPv6 addresses cause issues sometimes
}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)
voice_client_dict = {}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -af loudnorm=I=-16:TP=-1.5:LRA=11'
    
    # ---------------------------- Explanation --------------------------
    # I=-16: Integrated loudness target in LUFS (Loudness Units Full Scale). -16 LUFS is standard for online content.
    # TP=-1.5: True peak target in dB. This ensures no clipping.
    # LRA=11: Loudness range target, keeping the audio dynamic but within acceptable levels
}   

music_queue = {}  # Dictionary to store queues for each guild
timeout_timers = {}  # Dictionary to store timers for each voice channel