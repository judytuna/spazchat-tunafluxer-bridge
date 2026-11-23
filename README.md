# spaz.radio -> tunaFluxer bridge (one-way)

Mirrors spaz.radio's live chat into one tunaFluxer text channel. Each message
shows the spaz.radio name, like "dj_whoever (spaz)".

How spaz.radio chat works (from github.com/greenjon/spazradio, the Android app):
- Live chat is MQTT over WebSocket: wss://radio.spaz.org:1885/mqtt, topic `spazradio`.
- Payload is JSON `{"user": "...", "message": "..."}`. No login.
- History (last 100) is at https://radio.spaz.org/djdash/chatlog.
- The server is run by the spaz.radio folks, not in that repo.

The bridge only subscribes. It posts nothing to spaz.radio and does not appear
in its online list.

## 1. Make the community and channel
In tunaFluxer: add a community (e.g. "spaz test"), and a text channel (e.g. #spaz).
Keep it invite-only like the others.

## 2. Make a webhook for that channel
Look in the channel's settings for Integrations or Webhooks, create one, copy its URL.

If there's no webhook screen (Fluxer's docs only show the API way):
1. User Settings > Applications > new application > Regenerate the bot token.
2. Tick "bot", copy the Authorize URL, open it, pick the "spaz test" community.
3. Find the API base:  `curl -s https://chat.judytuna.com/.well-known/fluxer | jq .endpoints`
4. Get the channel id (right-click the channel, Copy ID, if offered), then:
   ```
   curl -s -X POST "$API/v1/channels/CHANNEL_ID/webhooks" \
     -H "Authorization: Bot $BOT_TOKEN" -H "Content-Type: application/json" \
     -d '{"name":"spaz.radio"}'
   ```
   The reply has `id` and `token` (shown once). Webhook URL = `$API/v1/webhooks/ID/TOKEN`.

Test it from your Mac:
```
curl -s -X POST "$WEBHOOK_URL" -H "Content-Type: application/json" \
  -d '{"content":"hello from the bridge","username":"test (spaz)"}'
```

## 3. Run it on the VPS
From your Mac:
```
scp -r spaz-bridge fluxer:~/
ssh fluxer
cd ~/spaz-bridge && cp .env.example .env && nano .env   # paste FLUXER_WEBHOOK_URL
sudo docker compose up -d --build
sudo docker compose logs -f
```
You should see "connected to spaz.radio: Success". Say something in spaz.radio chat to test.

If the log shows a certificate error, set `SPAZ_TLS_INSECURE=1` in .env and
`sudo docker compose up -d`. (The Android app skips certificate checks too.)

Stop: `sudo docker compose down`. Update: edit, then `sudo docker compose up -d --build`.

## Notes
- Outbound only: no firewall ports to open.
- `@` in spaz messages gets a zero-width space so nobody can ping @everyone.
- Messages sent while the bridge is down are not backfilled.
- Two-way (tunaFluxer -> spaz.radio) needs a Fluxer bot on the gateway that
  publishes to the `spazradio` topic. That posts into spaz.radio's public chat,
  so ask its operators first.
