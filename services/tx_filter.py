# services/tx_filter.py
from datetime import datetime

def filter_transactions(transactions, address, min_val=0.0, max_val=None,
                       start_date=None, end_date=None, direction='all'):
    """
    將 'transactions' (list of dict) 依多重條件過濾：
      - min_val / max_val
      - start_date / end_date (日期)
      - direction: 'all'/'in'/'out'
      - address: 使用者輸入的目標地址(小寫)
    回傳過濾後的新 list
    """
    address_lower = address.lower()
    filtered = []

    for tx in transactions:
        # 1) 金額篩選
        val = float(tx["value"]) / 10**18
        if val < min_val:
            continue
        if max_val is not None and val > max_val:
            continue

        # 2) 時間篩選
        tstamp = int(tx["timeStamp"])
        dt_obj = datetime.fromtimestamp(tstamp)
        if start_date and dt_obj.date() < start_date:
            continue
        if end_date and dt_obj.date() > end_date:
            continue

        # 3) 流向篩選
        f_addr = tx["from"].lower()
        t_addr = tx["to"].lower()

        if direction == 'in' and t_addr != address_lower:
            continue
        if direction == 'out' and f_addr != address_lower:
            continue

        # 符合 => 補充處理
        tx["value_ether"] = val
        tx["time_str"] = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        filtered.append(tx)

    return filtered
