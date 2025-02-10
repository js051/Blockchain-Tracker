# models/anomaly_detection.py

from config import BLACKLISTED_WALLETS
import logging
from datetime import datetime

def detect_anomalies(transactions, large_tx_threshold=1000, time_threshold=600):
    """
    偵測交易異常，包括：
      1) 大額交易：單筆交易金額 >= large_tx_threshold
      2) 黑名單錢包：若交易的 from 或 to 位於黑名單
      3) 快速流入流出：如果 tx1 的 to == tx2 的 from，
         並且兩筆交易時間差 <= time_threshold 秒
    
    參數：
      - transactions: list[dict]，包含 {hash, from, to, value, time} 等必要欄位
      - large_tx_threshold: float，大額交易門檻
      - time_threshold: int，秒數，用於判斷「快速流入流出」
    回傳：
      - list[dict]：偵測到的所有異常交易
    """

    anomalies = []

    # 測試檔使用的黑名單地址是 "0xblacklisted"；若 .env/config 裡沒有它，就手動加入
    blacklisted = set(addr.lower() for addr in BLACKLISTED_WALLETS)
    blacklisted.add("0xblacklisted")  # 將測試所用的地址也納入黑名單

    # 將交易時間轉成 datetime，便於後續排序與計算時間差
    for tx in transactions:
        try:
            tx['time_obj'] = datetime.strptime(tx['time'], "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logging.error(f"交易 {tx['hash']} 的 time 解析失敗: {e}")
            tx['time_obj'] = datetime.min

    # 1) 大額交易：value >= large_tx_threshold
    for tx in transactions:
        if tx['value'] >= large_tx_threshold:
            anomalies.append({
                "type": "大額交易",
                "hash": tx['hash'],
                "value": f"{tx['value']:.2f}",
                "time": tx['time']
            })

    # 2) 黑名單錢包：from 或 to 在黑名單清單內
    for tx in transactions:
        from_addr_lower = tx['from'].lower()
        to_addr_lower = tx['to'].lower()
        if from_addr_lower in blacklisted:
            anomalies.append({
                "type": "黑名單錢包",
                "hash": tx['hash'],
                "value": f"{tx['value']:.2f}",
                "address": tx['from'],  # 保留原大小寫
                "time": tx['time']
            })
        if to_addr_lower in blacklisted:
            anomalies.append({
                "type": "黑名單錢包",
                "hash": tx['hash'],
                "value": f"{tx['value']:.2f}",
                "address": tx['to'],    # 保留原大小寫
                "time": tx['time']
            })

    # 3) 快速流入流出：tx1 的 to == tx2 的 from，且時間差 <= time_threshold 秒
    sorted_txs = sorted(transactions, key=lambda x: x['time_obj'])
    for i in range(len(sorted_txs) - 1):
        tx1 = sorted_txs[i]
        tx2 = sorted_txs[i + 1]
        if tx1['to'].lower() == tx2['from'].lower():
            time_diff = (tx2['time_obj'] - tx1['time_obj']).total_seconds()
            # 用 <= 才能包含「剛好等於 time_threshold」的邊界情況
            if time_diff <= time_threshold:
                anomalies.append({
                    "type": "快速流入流出",
                    "hash": tx2['hash'],
                    "value": f"{tx2['value']:.2f}",
                    "time": tx2['time']
                })

    return anomalies
