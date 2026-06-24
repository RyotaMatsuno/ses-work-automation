import socket

# ポート8080が開いているか確認
s = socket.socket()
s.settimeout(2)
try:
    result = s.connect(("localhost", 8080))
    print("8080: 接続OK")
except Exception as e:
    print(f"8080: 接続失敗 → {e}")
finally:
    s.close()

# 127.0.0.1でも確認
s2 = socket.socket()
s2.settimeout(2)
try:
    result = s2.connect(("127.0.0.1", 8080))
    print("127.0.0.1:8080: 接続OK")
except Exception as e:
    print(f"127.0.0.1:8080: 接続失敗 → {e}")
finally:
    s2.close()
