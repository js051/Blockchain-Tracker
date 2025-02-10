# tests/conftest.py
import pytest
from dotenv import load_dotenv
import os

@pytest.fixture(scope='session', autouse=True)
def load_env():
    load_dotenv()  # 加載 .env 檔案
