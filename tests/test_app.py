# tests/test_app.py
import unittest
from unittest.mock import patch
from app import app

class TestApp(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True  # 啟用測試模式
        app.config['WTF_CSRF_ENABLED'] = False  # 禁用 CSRF
        self.app = app.test_client()
        self.app.testing = True

    def test_index_get(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("金流追查系統", response.get_data(as_text=True))

    @patch('app.requests.get')
    def test_invalid_blockchain(self, mock_get):
        response = self.app.post('/', data={
            "blockchain": "invalid",
            "address": "0x1234567890abcdef1234567890abcdef12345678",
            "min_value": "0",
            "max_value": "100",
            "page": "1"
        })
        self.assertEqual(response.status_code, 200)
        # 由於表單驗證失敗，錯誤訊息應為 "表單驗證失敗。請檢查輸入。"
        self.assertIn("表單驗證失敗。請檢查輸入。", response.get_data(as_text=True))

    @patch('app.requests.get')
    def test_index_post_valid(self, mock_get):
        # 模擬 API 回應
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "1",
            "message": "OK",
            "result": [
                {"hash": "0xabc", "from": "0xfromaddress", "to": "0xtoaddress", "value": "10000000000000000000", "timeStamp": "1609459200"}
            ]
        }

        response = self.app.post('/', data={
            "blockchain": "ethereum",
            "address": "0x1234567890abcdef1234567890abcdef12345678",
            "min_value": "0",
            "max_value": "100",
            "page": "1"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("查詢結果", response.get_data(as_text=True))

    @patch('app.requests.get')
    def test_no_transactions(self, mock_get):
        # 模擬 API 回應無交易
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "1", "message": "OK", "result": []}

        response = self.app.post('/', data={
            "blockchain": "ethereum",
            "address": "0x1234567890abcdef1234567890abcdef12345678",
            "min_value": "0",
            "max_value": "100",
            "page": "1"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("該篩選條件下無交易記錄。", response.get_data(as_text=True))

    @patch('app.requests.get')
    def test_export(self, mock_get):
        # 模擬 API 回應
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "1",
            "message": "OK",
            "result": [
                {"hash": "0xabc", "from": "0xfromaddress", "to": "0xtoaddress", "value": "10000000000000000000", "timeStamp": "1609459200"}
            ]
        }

        # 執行查詢以設置 session['transactions']
        response = self.app.post('/', data={
            "blockchain": "ethereum",
            "address": "0x1234567890abcdef1234567890abcdef12345678",
            "min_value": "0",
            "max_value": "100",
            "page": "1"
        })
        self.assertEqual(response.status_code, 200)

        # 執行導出操作
        response = self.app.post('/export')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Disposition"], 'attachment; filename=transactions.csv')
        self.assertIn("交易哈希,來自,發送到,金額 (ETH),時間", response.get_data(as_text=True))

if __name__ == '__main__':
    unittest.main()
