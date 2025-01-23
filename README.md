---

# Video Downloader Bot Setup Guide

This guide provides step-by-step instructions to install and run the Video Downloader bot on a Linux system.
- Backend code uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) which is released under [The Unlicense](https://unlicense.org/). All rights for yt-dlp belong to its respective authors.
---

## 1. Install Required Packages

You can install the required dependencies using one of the following methods:

### Automatic Installation:
```bash
pip install -r scr/requirements.txt
```

### Manual Installation:
```bash
sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp
sudo apt update && sudo apt install ffmpeg -y
pip install python-telegram-bot python-dotenv
```
### 2. Create a Linux service

i.e. `sudo nano /etc/systemd/system/insta-bot.service` with content:

---

## 2. Configure the Service File

Create a service file for the bot using the following command:
```bash
sudo nano /etc/systemd/system/insta-bot.service
```

Add the following configuration to the file:
```ini
[Unit]
Description=Video Downloader Bot Service
After=network.target

[Service]
User=your_linux_user                                   # <====== REPLACE THIS
WorkingDirectory=/path/to/your/bot                     # <====== REPLACE THIS
ExecStart=/usr/bin/python3 /path/to/your/bot/main.py   # <====== REPLACE THIS
Restart=always
RestartSec=5
Environment="BOT_TOKEN=your_bot_token"                 # <====== REPLACE THIS
Environment="DEBUG=False"

[Install]
WantedBy=multi-user.target
```

### Notes:
- `User`: Replace `your_linux_user` with the username that will run the bot.
- `WorkingDirectory`: Replace with the absolute path to your bot's folder.
- `ExecStart`: The command to start your bot. Adjust if you're using a virtual environment.
- `Environment`: Provide required environment variables, such as `BOT_TOKEN`.
- `Restart=always`: Ensures the bot restarts automatically if it crashes.

---

## 3. Start the Bot Service

Reload the systemd daemon and start the bot service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable insta-bot.service
sudo systemctl start insta-bot.service
sudo systemctl status insta-bot.service
```

## Deploy with Docker

Alternatively, you can use Docker.

Edit `.env` file with the your secrets and run container.

```
docker build . -t insta-bot:latest
docker run -d --name insta-bot --restart always --env-file .env insta-bot:latest
```
or use builded image from Docker hub
```
docker run -d --name insta-bot --restart always --env-file .env ovchynnikov/load-bot-linux:latest
```
---

## Troubleshooting

- Check the status of the service:
  ```bash
  sudo systemctl status insta-bot.service
  ```
- View logs for more details:
  ```bash
  journalctl -u insta-bot.service
  ```

## Usage

Follow these simple steps to set up and use the bot:

### 1. Create Your Telegram Bot
- Follow this guide to create your Telegram bot and obtain the bot token:
  [How to Get Your Bot Token](https://www.freecodecamp.org/news/how-to-create-a-telegram-bot-using-python/).

### 2. Health Check
- Verify the bot is running by sending a message with the trigger word:
  **`ботяра`**

  If the bot is active, it will respond accordingly.

### 3. Start Using the Bot
- Once the bot is created and the Linux service is running:
  1. Send a URL from **YouTube Shorts**, **Instagram Reels**, or similar platforms to the bot.
  Example:
  ```bash
  https://youtube.com/shorts/kaTxVLGd6IE?si=YaUM3gYjr1kcXqTm
  ```
  3. Wait for the bot to process the URL and respond.

### Supported platforms by default:
```bash
instagram reels
tiktok
reddit
x.com
youtube shorts
```

### Additionaly bot can download videos from other sources (for example youtube). Usually videos shorter than 10 minutes works fine. Telegram limitation is 50MB for a video.
- To download full video from youtube add two asterisk before the url address.
Example:
```bash
  **https://www.youtube.com/watch?v=rxdu3whDVSM or with a space ** https://www.youtube.com/watch?v=rxdu3whDVSM
```
- Full list of supported sites here: [yt-dlp Supported Sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
---
