# QNA Counter Bot

Single-file polling bot (python-telegram-bot 22.8).

## What it does
- Owner sends `/live` to the bot in DM → bot posts the formatted QNA
  session message to **Channel 1**, with two buttons (NGL Link / QNA Ans)
  and a counter line ending in `➜ 𝟬𝟬`.
- Every new post that shows up in **Channel 2** (the QNA-answers channel)
  bumps the counter by +1 and edits the live post in Channel 1.
- Count is kept in a local `data.json` file (no database) so it survives
  restarts.

## Setup
1. Make the bot an **admin** in both channels (needs "post messages" +
   "edit messages" permission in Channel 1, and just needs to be a
   member/admin in Channel 2 to receive channel_post updates).
2. Get the numeric chat IDs of both channels (they look like `-100xxxxxxxxxx`).
   Easiest way: forward a message from each channel to `@userinfobot` or
   `@JsonDumpBot`.
3. Set environment variables (locally in a `.env`/shell, or in Railway's
   Variables tab):

   | Variable       | Description                              |
   |----------------|-------------------------------------------|
   | `BOT_TOKEN`    | Token from @BotFather                    |
   | `OWNER_ID`     | Your numeric Telegram user ID             |
   | `CHANNEL_1_ID` | Main channel (gets the /live post)        |
   | `CHANNEL_2_ID` | QNA answers channel (triggers the +1)     |

## Run locally
```bash
pip install -r requirements.txt
export BOT_TOKEN=xxx OWNER_ID=123 CHANNEL_1_ID=-100xxx CHANNEL_2_ID=-100yyy
python bot.py
```

## Deploy on Railway
1. Push this folder to a GitHub repo (or use Railway's "Deploy from local
   directory" / CLI).
2. New Project → Deploy from repo.
3. Add the 4 environment variables above in the Railway Variables tab.
4. Railway will pick up `requirements.txt` automatically and run the
   `worker` process defined in `Procfile`.
5. No database/plugin needed — `data.json` lives on the container's disk.
   Note: on Railway's default ephemeral filesystem, `data.json` resets if
   the container is rebuilt/redeployed (not on simple restarts). If you
   want the count to survive redeploys too, mount a Railway Volume at the
   project root, or say the word and I'll wire it to a tiny external
   store instead.

## Notes on the buttons
Telegram's Bot API only gives inline URL buttons one flat visual style —
there's no "primary/progress" color variant like in app UI kits. What you
get here is the closest real lever: both buttons placed side by side in
one row, with your requested bold-unicode labels and emoji.
