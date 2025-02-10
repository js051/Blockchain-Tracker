# app.py
'''
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
'''

import os
import logging
import requests
import json
import time
import csv
from io import StringIO
from collections import defaultdict

from flask import Flask, render_template, request, Response, jsonify, session
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Regexp, Optional, NumberRange
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache

# 載入 config 中的 API_KEY 與 BLACKLISTED_WALLETS
from config import BLOCKCHAIN_API_KEYS, BLACKLISTED_WALLETS

# models
from models.anomaly_detection import detect_anomalies
from models.data_processing import analyze_transactions

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')
app.config['SESSION_TYPE'] = 'filesystem'

Session(app)
csrf = CSRFProtect(app)

# Limit: 每日200、每小時50、每分鐘10
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour", "10 per minute"],
    storage_uri="memory://"  # 單機測試可用，生產環境建議用 Redis 等
)
limiter.init_app(app)

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

if app.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

BLOCKCHAIN_APIS = {
    "ethereum": "https://api.etherscan.io/api",
    "bsc": "https://api.bscscan.com/api",
    "polygon": "https://api.polygonscan.com/api"
}

COINGECKO_IDS = {
    "ethereum": "ethereum",
    "bsc": "binancecoin",
    "polygon": "polygon"
}

def get_usd_price_for_blockchain(blockchain):
    """ 從 Coingecko 抓取該鏈對 USD 匯率，快取 1 分鐘。 """
    if blockchain not in COINGECKO_IDS:
        return 1.0
    cg_id = COINGECKO_IDS[blockchain]
    cache_key = f"cg_price_{cg_id}"
    cached_price = cache.get(cache_key)
    if cached_price:
        return cached_price

    url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        price = data.get(cg_id, {}).get("usd", 0.0)
        if price <= 0:
            price = 1.0
        cache.set(cache_key, price, timeout=60)
        return price
    except Exception as e:
        logging.error(f"Coingecko API 錯誤: {e}")
        return 1.0

# Flask-WTF 表單
class QueryForm(FlaskForm):
    blockchain = SelectField(
        '選擇區塊鏈',
        choices=[('ethereum','Ethereum'),('bsc','Binance Smart Chain'),('polygon','Polygon')],
        validators=[DataRequired()]
    )
    address = StringField(
        '錢包地址',
        validators=[
            DataRequired(),
            Regexp(r'^0x(?:[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64})$', message="地址需 0x + 40 或 64 hex"),
        ]
    )
    min_value = DecimalField(
        '最小金額',
        validators=[Optional(), NumberRange(min=0)],
        default=0.0
    )
    max_value = DecimalField(
        '最大金額',
        validators=[Optional(), NumberRange(min=0)],
        default=None
    )
    page = HiddenField('Page', default=1)
    submit = SubmitField('查詢')

@app.route("/", methods=["GET","POST"])
def index():
    form = QueryForm()
    if request.method == "GET":
        return render_template("index.html", form=form)

    # POST
    if form.validate_on_submit():
        blockchain = form.blockchain.data
        address = form.address.data.strip()
        min_val = float(form.min_value.data or 0.0)
        max_val = float(form.max_value.data) if form.max_value.data else None

        # 分頁 (Etherscan/bscscan offset 預設)
        try:
            page_num = int(form.page.data) if form.page.data else 1
            if page_num < 1: page_num = 1
        except ValueError:
            page_num = 1

        if blockchain not in BLOCKCHAIN_APIS:
            return render_template("index.html", form=form, error="不支援的區塊鏈")

        api_key = BLOCKCHAIN_API_KEYS.get(blockchain, "")
        if not api_key:
            return render_template("index.html", form=form, error="API Key 未設定")

        # 匯率
        usd_price = get_usd_price_for_blockchain(blockchain)

        # 一次抓 10000 筆
        offset = 10000
        url = (f"{BLOCKCHAIN_APIS[blockchain]}?module=account&action=txlist"
               f"&address={address}&sort=desc&page={page_num}&offset={offset}"
               f"&apikey={api_key}")
        logging.debug(f"API URL: {url}")

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"API 請求失敗: {e}")
            return render_template("index.html", form=form, error=f"API 請求失敗: {e}")

        if data.get("status") != "1":
            err_msg = data.get("message","未知錯誤")
            return render_template("index.html", form=form, error=f"交易查詢失敗: {err_msg}")

        raw_txs = data.get("result", [])
        logging.debug(f"取得 {len(raw_txs)} 筆交易")

        # 依 min_val / max_val 篩選
        filtered_txs = []
        for tx in raw_txs:
            raw_value = tx.get("value","0")
            try:
                raw_value_int = int(raw_value)
            except:
                raw_value_int = 0
            native_val = raw_value_int / 10**18
            if native_val < min_val:
                continue
            if max_val is not None and native_val > max_val:
                continue
            # timeStamp => to time
            tstamp = tx.get("timeStamp","0")
            try:
                t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(tstamp)))
            except:
                t = "未知時間"

            tx["value"] = native_val
            tx["usd_value"] = round(native_val * usd_price, 2)
            tx["time"] = t

            filtered_txs.append(tx)

        if not filtered_txs:
            return render_template("index.html", form=form, error="該篩選條件下無交易記錄。")

        # 分析 & 異常
        summary = analyze_transactions(filtered_txs, address)
        anomalies = detect_anomalies(filtered_txs)
        anomaly_dict = defaultdict(list)
        for anom in anomalies:
            anomaly_dict[anom["hash"]].append(anom["type"])

        # 判斷是否還有下一頁
        has_next_page = (len(raw_txs) == offset)
        total_pages = page_num + 1 if has_next_page else page_num

        # 存 session 供 /export 和 /graph_data
        session["transactions"] = filtered_txs
        session["current_blockchain"] = blockchain
        session["usd_price"] = usd_price

        return render_template("result.html",
                               summary=summary,
                               anomalies=anomalies,
                               anomaly_dict=anomaly_dict,
                               transactions=filtered_txs,
                               total_pages=total_pages,
                               current_page=page_num,
                               address=address,
                               form=form
                               )
    else:
        return render_template("index.html", form=form, error="表單驗證失敗。請檢查輸入。")

@app.route("/export", methods=["POST"])
@limiter.limit("5 per minute")
def export():
    txs = session.get("transactions", [])
    if not txs:
        return jsonify({"error":"無交易資料"}),400

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["交易哈希","來自","發送到","金額(原生)","金額(USD)","時間"])
    for tx in txs:
        writer.writerow([
            tx.get("hash"),
            tx.get("from"),
            tx.get("to"),
            tx.get("value"),
            tx.get("usd_value"),
            tx.get("time")
        ])
    output = si.getvalue()
    return Response(output, mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=transactions.csv"})

@app.route("/graph")
def graph():
    return render_template("graph.html")

@app.route("/graph_data")
def graph_data():
    transactions = session.get("transactions", [])
    if not transactions:
        # 若沒有資料，回傳一組假資料方便前端測試
        dummy_data = {
            "nodes": [
                {"id": "0x111", "is_blacklisted": False},
                {"id": "0x222", "is_blacklisted": True},
                {"id": "0x333", "is_blacklisted": False}
            ],
            "links": [
                {"source": "0x111", "target": "0x222", "value": 50},
                {"source": "0x222", "target": "0x333", "value": 120},
                {"source": "0x333", "target": "0x111", "value": 5}
            ]
        }
        app.logger.debug("回傳假資料: %s", dummy_data)
        return jsonify(dummy_data)

    # 取得黑名單（全部轉為小寫）
    blacklisted_set = {addr.lower() for addr in BLACKLISTED_WALLETS}
    # 強制加入測試用黑名單地址
    blacklisted_set.add("0xblacklisted")

    nodes_map = {}
    links = []

    for tx in transactions:
        f = (tx.get("from", "未知") or "未知").lower()
        t = (tx.get("to", "未知") or "未知").lower()
        # 如果 usd_value 不是數字，強制轉換為 0.0
        try:
            usd_val = float(tx.get("usd_value", 0))
        except Exception as e:
            app.logger.error("轉換 usd_value 失敗，tx=%s, error=%s", tx, e)
            usd_val = 0.0

        # 排除自連（若 from == to 則不加入連線，但仍可建立節點）
        if f == t:
            app.logger.debug("發現自連交易，忽略連線: %s -> %s", f, t)
        else:
            links.append({
                "source": f,
                "target": t,
                "value": usd_val
            })

        if f not in nodes_map:
            nodes_map[f] = {"id": f, "is_blacklisted": (f in blacklisted_set)}
        if t not in nodes_map:
            nodes_map[t] = {"id": t, "is_blacklisted": (t in blacklisted_set)}

    nodes = list(nodes_map.values())
    ret = {"nodes": nodes, "links": links}
    app.logger.debug("graph_data 回傳資料: %s", ret)
    return jsonify(ret)

@app.route("/graph_data_nhop")
def graph_data_nhop():
    """
    以 session["address"] 為起點，做 n-hop BFS (含 from->to / to->from 都視為相鄰)。
    只在 session["transactions"] 中尋找，不會額外呼叫區塊鏈 API。
    若要真正跨地址查詢，需要在 BFS 過程打 API。
    """
    # 讀取 hop 參數
    hop_str = request.args.get("hop", "1")
    try:
        hop = int(hop_str)
    except ValueError:
        hop = 1
    if hop < 1:
        hop = 1

    # 從 session 讀取原查詢地址 (若無就回傳空)
    start_address = session.get("address")
    if not start_address:
        return jsonify({"error":"no start address in session"}), 400

    txs = session.get("transactions", [])
    if not txs:
        return jsonify({"error":"no transactions in session"}), 400

    # 建立鄰接表 adjacency: { addr: set([addr2, addr3, ...]) }
    # 以及 links_map: 用於記錄 (a,b) => 該筆交易(USD, time?)
    from collections import defaultdict
    adjacency = defaultdict(set)
    links_map = defaultdict(list)

    for tx in txs:
        f = tx.get("from","").lower()
        t = tx.get("to","").lower()
        val = tx.get("usd_value", 0.0)
        # 雙向紀錄 => BFS 方便
        adjacency[f].add(t)
        adjacency[t].add(f)
        # 儲存連線資訊 (可能多筆)
        links_map[(f,t)].append(tx)
        links_map[(t,f)].append(tx)  # 不一定要雙向都加，但若想顯示 2 向交易可保留

    # BFS
    from collections import deque
    visited = set()
    queue = deque()
    queue.append((start_address.lower(), 0))
    visited.add(start_address.lower())

    # 要收集的 "nodes" 和 "links"
    nodes_set = set()
    edges = []

    # 每個地址都做 is_blacklisted 判斷
    black_set = {b.lower() for b in BLACKLISTED_WALLETS}
    black_set.add("0xblacklisted")

    while queue:
        current, depth = queue.popleft()
        # 加入 nodes_set
        nodes_set.add(current)

        if depth >= hop:
            continue

        # 取得下一層鄰居
        neighbors = adjacency[current]
        for nb in neighbors:
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, depth+1))

            # 找出 current->nb 的交易 link
            if (current, nb) in links_map:
                for tx in links_map[(current, nb)]:
                    # 預設以 usd_value 做 link value
                    edges.append({
                        "source": current,
                        "target": nb,
                        "value": tx.get("usd_value", 0.0),
                        "time": tx.get("time", "未知")
                    })

    # 整理 nodes
    nodes_list = []
    for addr in nodes_set:
        nodes_list.append({
            "id": addr,
            "is_blacklisted": (addr in black_set)
        })

    return jsonify({"nodes": nodes_list, "links": edges})


if __name__=="__main__":
    debug_mode = os.getenv("FLASK_DEBUG","False")=="True"
    app.run(debug=debug_mode)
