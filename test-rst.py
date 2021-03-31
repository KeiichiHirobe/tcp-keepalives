import io
import os
import select
import socket
import time
import utils

# 以下はnetwork namespaceを新たに作成するためか、tcp_fin_timeoutの変更等が継承されないためコメントアウト
# utils.new_ns()

port = 1

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
s.bind(('127.0.0.1', port))
s.listen(16)

tcpdump = utils.tcpdump_start(port)
c = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

time.sleep(1)
utils.ss(port)

c.connect(('127.0.0.1', port))
time.sleep(1)
print("[c] client connect")
utils.ss(port)

x, _ = s.accept()
time.sleep(1)
print("[x] server accept")
utils.ss(port)

# for num in range(3):
#    print("[x] send")
#    c.send(b"hello world")

x.shutdown(socket.SHUT_WR)
time.sleep(1)
print("[x] server shutdown(SHUT_WR)")
utils.ss(port)

x.close()
time.sleep(1)
print("[x] server close socket")
utils.ss(port)

for num in range(3):
    print("[x] send")
    c.send(b"hello world")
    time.sleep(1)
    utils.ss(port)

print("#####just ss outputs from now#####")
time.sleep(1)
utils.ss(port)
time.sleep(1)
utils.ss(port)
time.sleep(1)
utils.ss(port)
