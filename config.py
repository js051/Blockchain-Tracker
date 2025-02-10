# config.py
import os
import json
from dotenv import load_dotenv
import logging

# 加載 .env 檔案
load_dotenv()

# 日誌設置
logging.basicConfig(level=logging.DEBUG)

# 取得 API Keys
BLOCKCHAIN_API_KEYS = {
    "ethereum": os.getenv("ETHERSCAN_API_KEY"),
    "bsc": os.getenv("BSCSCAN_API_KEY"),
    "polygon": os.getenv("POLYGONSCAN_API_KEY")
}

# 檢查必需的 API Keys 是否設置
required_keys = ["ETHERSCAN_API_KEY", "BSCSCAN_API_KEY", "POLYGONSCAN_API_KEY"]
for key in required_keys:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"{key} 必須在環境變數中設置。")
    logging.debug(f"{key} 已設置為: {value}")

# 取得黑名單錢包地址
BLACKLISTED_WALLETS = json.loads(os.getenv("BLACKLISTED_WALLETS", "[]"))
logging.debug(f"黑名單錢包地址: {BLACKLISTED_WALLETS}")
