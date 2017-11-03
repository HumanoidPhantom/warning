import sys
import server
import client
import socket
from netifaces import interfaces, ifaddresses, AF_INET
import threading

TYPE = 'client'
MAX_CONNECTIONS_NUMBER = 10
RECV_BUFFER = 4048
RECV_MSG_LEN = 4


def get_avail_ips():
    addr_text = ''
    for iface_name in interfaces():

        tmp_address = ifaddresses(iface_name).setdefault(AF_INET, [{'addr': ''}])[0]['addr']

        if tmp_address != '':
            if tmp_address[:6] == '172.17':
                addr_text += 'local IP: ' + tmp_address + '; '
            elif tmp_address == '127.0.0.1':
                pass
            else:
                addr_text += 'public IP: ' + tmp_address + '; '

    if addr_text != '':
        addr_text = 'your ' + addr_text

    return addr_text


def get_additional_info():

    addr_text = get_avail_ips()

    while True:

        host = input("Host/IP-address (%sprint [exit] to leave): " % addr_text)
        if host == 'exit':
            print('Bye-bye')
            sys.exit()
        elif len(host) == 0:
            print('Too short answer, try again')
            continue

        while True:
            port = input("Port (print [back] to change host): ")
            if port == 'back':
                host = -1
                break
            elif len(port) == 0:
                print('Too short answer. Try again')
                continue
            elif not port.isdigit() or int(port) < 1 or int(port) > 65535:
                print('\nWrong value')
                continue
            else:
                break

        if host == -1:
            continue

        return host, int(port)


def get_connection_info():

    while True:

        host = input("Host/IP-address (print [exit] to change type): ")
        if host == 'exit':
            print('Bye-bye')
            sys.exit()
        elif len(host) == 0:
            print('Too short answer, try again')
            continue

        while True:
            port = input("Port (print [back] to change host): ")
            if port == 'back':
                host = -1
                break
            elif len(port) == 0:
                print('Too short answer. Try again')
                continue
            elif not port.isdigit() or int(port) < 1 or int(port) > 65535:
                print('\nWrong value')
                continue
            else:
                break

        if host == -1:
            continue

        return True, True, host, int(port)


class WarningClient(threading.Thread):
    def __init__(self, host, port, max_connections, recv_buffer, recv_msg_len):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.clients = [sys.stdin]
        self.clients_active = []
        self.clients_names = {}
        self.running = True
        self.max_connections_number = max_connections
        self.recv_buffer = recv_buffer
        self.recv_msg_len = recv_msg_len
        self.show_income = True
        self.stickers_text = ''


def main():

    while True:
        host_own, port_own = get_additional_info()
        go_back, create, host, port = get_connection_info()

        if go_back:
            break

    chat_server = server.ChatServer(host, port, MAX_CONNECTIONS_NUMBER, RECV_BUFFER, RECV_MSG_LEN)
    chat_server.start()


if __name__ == '__main__':
    main()
