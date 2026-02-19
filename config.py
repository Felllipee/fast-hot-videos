import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH")
    BIN_CHANNEL = int(os.getenv("BIN_CHANNEL", 0))
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
    PORT = int(os.getenv("PORT", 8080)) # Changed default to match project
    WEB_SERVER_BIND_ADDRESS = os.getenv("WEB_SERVER_BIND_ADDRESS", "0.0.0.0")
    # IPv6 can cause delays on some networks
    IPV6 = False # Manual override for VPN/Domain
    BASE_URL = os.getenv("BASE_URL") # Manual override for VPN/Domain
    
    # Validation
    if not BOT_TOKEN or not API_ID or not API_HASH:
        raise ValueError("BOT_TOKEN, API_ID, and API_HASH must be set in .env")
