from flask import Flask

app = Flask(__name__)

from app import app  # 解决循环导入
