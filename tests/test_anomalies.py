# tests/test_anomalies.py
import unittest
from models.anomaly_detection import detect_anomalies

class TestAnomalyDetection(unittest.TestCase):
    def test_detect_anomalies(self):
        transactions = [
            {"hash": "0x1", "from": "0xfrom1", "to": "0xto1", "value": 500.0, "time": "2021-01-01 00:00:00"},
            {"hash": "0x2", "from": "0xto1", "to": "0xto2", "value": 2000.0, "time": "2021-01-01 00:10:00"},
            {"hash": "0x3", "from": "0xto2", "to": "0xfrom2", "value": 300.0, "time": "2021-01-01 01:00:00"},
            {"hash": "0x4", "from": "0xblacklisted", "to": "0xto3", "value": 100.0, "time": "2021-01-01 02:00:00"},
        ]
        expected = [
            {"type": "大額交易", "hash": "0x2", "value": "2000.00", "time": "2021-01-01 00:10:00"},
            {"type": "快速流入流出", "hash": "0x2", "value": "2000.00", "time": "2021-01-01 00:10:00"},
            {"type": "黑名單錢包", "hash": "0x4", "value": "100.00", "address": "0xblacklisted", "time": "2021-01-01 02:00:00"},
        ]
        result = detect_anomalies(transactions, large_tx_threshold=1000, time_threshold=600)
        self.assertEqual(len(result), len(expected))
        for anomaly in expected:
            self.assertIn(anomaly, result)

    def test_detect_blacklisted_wallets(self):
        transactions = [
            {"hash": "0x1", "from": "0xfrom1", "to": "0xblacklisted", "value": 5.0, "time": "2021-01-01 00:00:00"},
            {"hash": "0x2", "from": "0xfrom2", "to": "0xto2", "value": 3.0, "time": "2021-01-01 01:00:00"},
            {"hash": "0x3", "from": "0xblacklisted", "to": "0xto3", "value": 2.0, "time": "2021-01-01 02:00:00"},
        ]
        expected = [
            {"type": "黑名單錢包", "hash": "0x1", "value": "5.00", "address": "0xblacklisted", "time": "2021-01-01 00:00:00"},
            {"type": "黑名單錢包", "hash": "0x3", "value": "2.00", "address": "0xblacklisted", "time": "2021-01-01 02:00:00"},
        ]
        result = detect_anomalies(transactions)
        self.assertEqual(len(result), len(expected))
        for anomaly in expected:
            self.assertIn(anomaly, result)

    def test_detect_quick_in_out(self):
        transactions = [
            {"hash": "0x1", "from": "0xfrom1", "to": "0xto1", "value": 5.0, "time": "2021-01-01 00:00:00"},
            {"hash": "0x2", "from": "0xto1", "to": "0xto2", "value": 3.0, "time": "2021-01-01 00:10:00"},
            {"hash": "0x3", "from": "0xto2", "to": "0xfrom2", "value": 2.0, "time": "2021-01-01 01:00:00"},
        ]
        expected = [
            {"type": "快速流入流出", "hash": "0x2", "value": "3.00", "time": "2021-01-01 00:10:00"}
        ]
        result = detect_anomalies(transactions, time_threshold=600)  # 10 分鐘
        self.assertEqual(len(result), len(expected))
        for anomaly in expected:
            self.assertIn(anomaly, result)

    def test_detect_large_transactions(self):
        transactions = [
            {"hash": "0x1", "from": "0xfrom1", "to": "0xto1", "value": 5.0, "time": "2021-01-01 00:00:00"},
            {"hash": "0x2", "from": "0xfrom2", "to": "0xto2", "value": 15.0, "time": "2021-01-01 01:00:00"},
        ]
        expected = [
            {"type": "大額交易", "hash": "0x2", "value": "15.00", "time": "2021-01-01 01:00:00"}
        ]
        result = detect_anomalies(transactions, large_tx_threshold=10)
        self.assertEqual(len(result), len(expected))
        self.assertIn(expected[0], result)

    def test_detect_anomalies_empty_transactions(self):
        transactions = []
        result = detect_anomalies(transactions)
        self.assertEqual(len(result), 0)

    def test_detect_anomalies_extreme_values(self):
        transactions = [
            {"hash": "0x1", "from": "0xfrom1", "to": "0xto1", "value": 1e12, "time": "2021-01-01 00:00:00"},  # 非常大金額
            {"hash": "0x2", "from": "0xto1", "to": "0xto2", "value": -100.0, "time": "2021-01-01 00:10:00"},  # 負數金額
        ]
        expected = [
            {"type": "大額交易", "hash": "0x1", "value": "1000000000000.00", "time": "2021-01-01 00:00:00"},
            {"type": "快速流入流出", "hash": "0x2", "value": "-100.00", "time": "2021-01-01 00:10:00"},
        ]
        result = detect_anomalies(transactions, large_tx_threshold=1e6)
        self.assertEqual(len(result), len(expected))
        for anomaly in expected:
            self.assertIn(anomaly, result)

if __name__ == '__main__':
    unittest.main()
