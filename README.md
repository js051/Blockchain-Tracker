# Blockchain Tracker

這是一個區塊鏈金流追蹤系統的原型專案，使用 Flask 作為後端，
並利用 D3.js 實現資金流向的可視化。  
## 主要功能
- 透過 Etherscan/BSCSCAN API 取得交易資料
- 基本異常偵測（大額交易、黑名單錢包、快速流入流出）
- CSV 匯出與 D3.js 力導向圖視覺化

## 安裝與執行
1. 克隆專案： `git clone <repository_url>`
2. 安裝相依套件： `pip install -r requirements.txt`
3. 建立 `.env`（參考 `.env.example`）
4. 執行專案： `python app.py`
