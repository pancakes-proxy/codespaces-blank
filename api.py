from fastapi import FastAPI, HTTPException
import subprocess
from pydantic import BaseModel

app = FastAPI()

# Sample bot data (You can replace this with database entries)
bots = {
    "bot1": {"name": "TETO", "status": "N/A", "directory": "/home/server/wdiscordbot/", "update_url": "https://github.com/pancakes-proxy/wdiscordbot.git"},
}

class BotAction(BaseModel):
    bot_id: str

# Endpoint to list all running bots
@app.get("/api/bots")
def get_bots():
    return bots

# Shutdown a bot
@app.post("/api/bot/{bot_id}/shutdown")
def shutdown_bot(bot_id: str):
    if bot_id not in bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    try:
        subprocess.run(["pm2", "stop", bot_id], check=True)
        bots[bot_id]["status"] = "Stopped"
        return {"message": f"Bot {bot_id} shut down successfully"}
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Failed to shut down bot")

# Restart a bot
@app.post("/api/bot/{bot_id}/restart")
def restart_bot(bot_id: str):
    if bot_id not in bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    try:
        subprocess.run(["pm2", "restart", bot_id], check=True)
        bots[bot_id]["status"] = "Running"
        return {"message": f"Bot {bot_id} restarted successfully"}
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Failed to restart bot")

# Update & restart a bot
@app.post("/api/bot/{bot_id}/update")
def update_bot(bot_id: str):
    if bot_id not in bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    bot_info = bots[bot_id]
    update_cmd = f"cd {bot_info['directory']} && wget -O bot.zip {bot_info['update_url']} && unzip -o bot.zip && pip install -r requirements.txt && pm2 restart {bot_id}"

    try:
        subprocess.run(update_cmd, shell=True, check=True)
        bots[bot_id]["status"] = "Running"
        return {"message": f"Bot {bot_id} updated and restarted successfully"}
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Failed to update bot")

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)