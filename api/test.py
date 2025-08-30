from pyrogram import Client

API_ID = 1626657
API_HASH = "b0d1b4e33de690e1783dfbc547b6c18a"

app = Client("uploader", api_id=API_ID, api_hash=API_HASH)
app.run()
