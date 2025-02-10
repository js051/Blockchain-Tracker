# models/data_processing.py
import logging

def analyze_transactions(transactions, wallet_address):
    flow_in = []
    flow_out = []
    wallet_address_lower = wallet_address.lower()
    logging.debug(f"分析錢包地址: {wallet_address_lower}")

    for tx in transactions:
        tx_to = tx.get("to", "").lower()
        tx_from = tx.get("from", "").lower()

        if tx_to == wallet_address_lower:
            flow_in.append({
                "hash": tx["hash"],
                "from": tx["from"],
                "value": tx["value"],  # 保持為數字類型
                "time": tx["time"]     # 已經在 app.py 中添加
            })
            logging.debug(f"流入交易: {tx['hash']} 金額: {tx['value']} ETH")
        elif tx_from == wallet_address_lower:
            flow_out.append({
                "hash": tx["hash"],
                "to": tx["to"],
                "value": tx["value"],  # 保持為數字類型
                "time": tx["time"]     # 已經在 app.py 中添加
            })
            logging.debug(f"流出交易: {tx['hash']} 金額: {tx['value']} ETH")

    total_in = round(sum(tx["value"] for tx in flow_in), 2)
    total_out = round(sum(tx["value"] for tx in flow_out), 2)

    summary = {
        "total_in": total_in,      # 數字類型
        "total_out": total_out,    # 數字類型
        "count_in": len(flow_in),
        "count_out": len(flow_out),
        "flow_in": flow_in,
        "flow_out": flow_out
    }

    logging.debug(f"流入總金額: {summary['total_in']} ETH, 流出總金額: {summary['total_out']} ETH")
    logging.debug(f"流入交易數量: {summary['count_in']}, 流出交易數量: {summary['count_out']}")

    return summary
