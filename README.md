### 1. Installation of packages
```
pip install -r requirements.txt
```
  
or install manually 
```
sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
sudo apt update && sudo apt install ffmpeg -y
pip install python-telegram-bot python-dotenv
sudo chmod a+rx /usr/local/bin/yt-dlp
```
### 2. sudo nano /etc/systemd/system/insta-bot.service

```ini
[Unit]
Description=Instagram Bot Service
After=network.target

[Service]
User=your_linux_user                                   <====== CHANGE THIS
WorkingDirectory=/path/to/your/bot                     <====== CHANGE THIS
ExecStart=/usr/bin/python3 /path/to/your/bot/main.py   <====== CHANGE THIS
Restart=always
RestartSec=5
Environment="BOT_TOKEN=bot_token"                      <====== CHANGE THIS
Environment="DEBUG=False"

[Install]
WantedBy=multi-user.target
```

```
User: Replace your_linux_user with the username running the bot.
WorkingDirectory: Path to the bot folder.
ExecStart: The command to start your bot (adjust if you're using venv).
Environment: Pass environment variables like the BOT_TOKEN or DEBUG.
Restart=always: Restarts the bot if it crashes.
```
### 3. Start deamon
```
sudo systemctl daemon-reload
sudo systemctl enable insta-bot.service
sudo systemctl start insta-bot.service
sudo systemctl status insta-bot.service
```
