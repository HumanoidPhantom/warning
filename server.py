from socket import *
import threading
import sys

clients = []
lastMessages = []

PORT = 9090
HOST = ""


def handle_client(c):
    global lastMessages
    data = c.recv(100000)
    if data.decode() == "-1":
        if len(lastMessages):
            answer = '\r\n'.join(lastMessages)
        else:
            answer = 'no messages yet'
        c.send(answer.encode())
    else:
        lastMessages.append(data.decode())
        if len(lastMessages) > 10:
            lastMessages = lastMessages[1:]
        for item in clients:
            answer = "message sent"
            item.send(answer.encode())
    c.close()
    return


def run_thread(conn, addr):
    print("New user with", addr[0] + ":" + str(addr[1]))
    while True:
        data = conn.recv(1024)
        reply = b'OK' + data
        print(reply)
        conn.sendall(reply)

    conn.close()


def run():
    print('Waiting for connections on port %s' % PORT)

    while True:
        conn, addr = s.accept()
        threading.Thread(target=run_thread, args=(conn, addr)).start()

s = socket(AF_INET, SOCK_STREAM)
s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

s.bind(("", PORT))
# try:
# except error:
#     print("Bind failed %s" % error)
#     sys.exit()
print(s)
s.listen(100)
print("Here")
while True:
    # conn, addr = s.accept()
    c, a = s.accept()
    print(a)
    matches = next((True for x in clients if x == c), False)
    if not matches:
        clients.append(c)
    print(matches)
    print ("Wait for new one")
    t = threading.Thread(target=handle_client, args=(c,))
    t.start()
    # threading.Thread(target=handle_client, args=(conn, addr)).start()

