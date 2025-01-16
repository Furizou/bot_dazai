# 🤠 Dazai - Powerful Discord Bot
A feature-rich Discord music bot built with discord.py that supports playing songs from YouTube and Spotify, interactive controls, dynamic server-specific prefixes, and administrative commands. It leverages FFmpeg for audio playback and integrates with Docker and GitHub Actions for streamlined deployment.

## 📑 Features
- Play Music: Search and play songs from YouTube using URLs or search queries.
- Spotify Integration: Support for searching and playing tracks via Spotify links.
- Interactive Controls: Use Discord buttons for pause/resume, skip, stop, and viewing the queue.
- Dynamic Prefixes: Server-specific command prefixes customizable by administrators.
- Admin Commands: Commands like setprefix to modify bot settings per server.
- Robust Handling: Graceful error handling with informative Discord embeds.
- Docker & CI/CD: Preconfigured Dockerfile and GitHub Actions workflow for easy deployment.

## ⚙️ Installation
### Prerequisites
- Python 3.11 or higher
- Docker (optional, for containerized deployment)
- FFmpeg installed on the system (or use Docker image with FFmpeg)

### Running Locally
1. **Clone the repository**:
    ```sh
    git clone https://github.com/Furizou/bot_dazai.git
    cd bot_dazai
    ```
2. **Set up environment variables**: Create a `.env` file in the root directory and add:
   ```makefile
   DISCORD_TOKEN=your_discord_bot_token
   YOUTUBE_API_KEY=your_youtube_api_key
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   ```
3. **Install dependencies**:
   ```sh
    pip install -r requirements.txt
    ```
4. **Run the bot**:
   ```sh
    python main.py
    ```
### Running with Docker
1. **Build the Docker image**:
   ```sh
    docker build -t bot_dazai .
    ```
2. **Run the container**:
   ```sh
    docker run -d --name bot_dazai_container --env-file .env bot_dazai
    ```
or simply run as follow
```sh
docker compose up --build -d
```

## 🔎 Usage
Invite the bot to your Discord server using your bot's invite link with necessary permissions. Use the following prefix to interact with the bot & display available commands.
```shell
>help
```

## ⚒️ Contributing
Contributions, issues, and feature requests are welcome! Feel free to check [issues](https://github.com/Furizou/bot_dazai/issues) page.
