import sys
import tempfile
import socket
from netifaces import interfaces, ifaddresses, AF_INET
import threading
import atexit
import struct
import string
import hashlib
import select
import json
import subprocess
import os

TYPE = 'client'
MAX_CONNECTIONS_NUMBER = 10
RECV_BUFFER = 4048
RECV_MSG_LEN = 4
PORT = 9090
DEF_MESSAGE = '[m - send message, s - stickers, q - quit]\n'
CLIENT_FILE = 'files/client.list'
EDITOR = os.environ.get('EDITOR') if os.environ.get('EDITOR') else 'vim'

my_socket = None
user_login = ''
user_pass = ''
user_address = ''
exit_message = 'Disconnected from chat\n'
clients_names = {}
my_address = ''


def get_ip():
    addr = ''
    for iface_name in interfaces():

        tmp_address = ifaddresses(iface_name).setdefault(AF_INET, [{'addr': ''}])[0]['addr']

        if tmp_address != '' and tmp_address[:4] == '188.':
            addr = tmp_address

    return addr


def get_connection_info():
    change_create = True
    change_host = True
    host = -1

    while True:
        if change_create:
            command = input("Create new chat [n] / Connect to existing one [c] / [exit] to leave: ")
            if command == 'n':
                return -1, -1
            elif command == 'c':
                pass
            elif command == 'exit':
                print_to_console('Bye-bye\n', False)
                sys.exit()
            else:
                continue
        change_create = True

        if change_host:
            host = input("Host/IP-address (print [back] to change type): ")
            if host == 'back':
                continue
            elif len(host) == 0:
                print_to_console('Too short answer, try again', False)
                change_create = False
                continue
        change_host = True

        port = input("Port (print [back] to change host): ")
        if port == 'back':
            change_create = False
            continue
        elif len(port) == 0:
            print_to_console('Too short answer. Try again', False)
            change_create = False
            change_host = False
            continue
        elif not port.isdigit() or int(port) < 1 or int(port) > 65535:
            print_to_console('Wrong value', False)
            change_create = False
            change_host = False
            continue

        return host, int(port)


def init_stickers():
    with open('sticker.list', 'r') as f:
        sticker_list = {}
        for item in f.read().split('-'):
            tmp = item.split('sticker')
            if len(tmp) == 2:
                sticker_list[tmp[0]] = tmp[1]

    return sticker_list


def data_checker(msg, min_len, with_punctuation=False):

    allowed_chars = string.ascii_letters + string.digits + (string.punctuation if with_punctuation else '')

    while True:
        inp_data = input(msg)

        if inp_data == 'exit':
            stop()
        elif len(inp_data) < min_len:
            print_to_console('Too short answer. Try again.\n', False)
            continue

        good_pass = True
        for ch in inp_data:
            if ch not in allowed_chars:
                print_to_console('Restricted symbols were used\n', False)
                good_pass = False
                break

        if not good_pass:
            continue

        return inp_data


def print_to_console(msg, with_default=True):
    sys.stdout.write(msg)
    if with_default:
        sys.stdout.write(DEF_MESSAGE)
    sys.stdout.flush()


def open_editor():
    with open('initial.txt') as initial:
        initial_message = initial.read()

    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
        tf.write(initial_message.encode())
        tf.flush()
        subprocess.call([EDITOR, tf.name])

        tf.seek(0)

        with open(tf.name) as tmp:
            message = tmp.read().splitlines()

        res_message = ''
        for line in message:
            if not (len(line) > 3 and line[:3] == '###'):
                res_message += ('\n' if len(res_message) else '') + line

        return res_message


def receive_message(sock, msg_len, tot_data_len):
    data = ''

    while tot_data_len < msg_len:
        chunk = sock.recv(RECV_BUFFER)
        if not chunk:
            data = None
            break
        else:
            data += str(chunk.decode('utf-16'))
            tot_data_len += len(chunk)

    parts = data.split('+++', 1)
    if len(parts) == 2:
        return parts[0], parts[1]

    return '', ''


def send(addr, msg, print_error=False):
    msg = struct.pack('>I', len(msg)*2) + msg.encode('utf-16')
    ip, port = addr.split()

    result = False

    if port.isdigit():
        port = PORT if ip[:4] == '172.' else int(port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tmp_socket:
            tmp_socket.settimeout(2)
            try:
                tmp_socket.connect((ip, int(port)))
            except socket.error:
                if print_error:
                    print_to_console('It was not possible to connect to %s\n' % addr)
                result = False
            else:
                tmp_socket.send(msg)
                result = True
            tmp_socket.close()

    return result


def remove_client(addr):
    if addr in clients_names:
        del clients_names[addr]


def add_client(addr, login, passwd):
    clients_names[addr] = login

    with open(CLIENT_FILE, 'a') as f:
        clients_list = read_users_from_file()

        if login not in clients_list.keys():
            append_user_to_file(f, login, passwd)


def read_users_from_file():
    read_clients = open(CLIENT_FILE, 'r')

    line_clients = read_clients.read().splitlines()

    clients_list = {}
    for cl in line_clients:
        tmp = cl.split()
        clients_list[tmp[0]] = tmp[1]

    read_clients.close()

    return clients_list


def append_user_to_file(f, login, passwd):
    new_client = login + ' ' + passwd + '\n'
    f.write(new_client)


def broadcast(request_addr, msg):
    for addr in clients_names.copy():
        if request_addr != addr and not send(addr, msg):
            remove_client(addr)


def stop():
    if my_socket:
        my_socket.close()
    sys.exit()


def exit_handler():
    global my_socket

    if user_login != '':
        broadcast('', 'quit' + my_address + '+++' + user_login)

    print_to_console(exit_message, False)


atexit.register(exit_handler)


class WarningClient(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.host_own = get_ip()
        self.host = host
        self.port = port
        self.stickers = init_stickers()

    def run(self):
        self._bind_socket()
        self.authorize()
        self._run()

    def _bind_socket(self):
        global my_socket
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            my_socket.bind((self.host_own, PORT))
        except socket.error as msg:
            print_to_console('Cannot bind to the host: ', False)
            sys.exit()
        else:
            global my_address
            my_address = '%s %s' % (my_socket.getsockname()[0], my_socket.getsockname()[1])
            message = 'You almost entered the chat. Your internal address: %s\n' \
                      '(external IP/hostname and port specified in docker command ' \
                      'also could be used to connect to you)\n'\
                      % my_address

            print_to_console(message, False)

        my_socket.listen(MAX_CONNECTIONS_NUMBER)

    def authorize(self):
        login = data_checker('Login (allowed: [A-Za-z0-9], [exit] to leave): ', 1)
        passwd = data_checker('Password (at least 5 chars, allowed: ['
                              + 'A-Za-z0-9' + string.punctuation
                              + '] [exit] to leave): ', 5, True)

        hpasswd = hashlib.sha256(passwd.encode('utf-16')).hexdigest()

        global user_login
        global user_pass
        global my_socket

        user_login = login
        user_pass = hpasswd

        if self.host != -1:

            header = "auth" + my_address + '+++'
            if not send(self.host + ' ' + str(self.port), header + login + " " + hpasswd, True):
                stop()

        else:
            res = self.check_in_file(login + " " + hpasswd)

            if res[0]:
                print_to_console('')

    def check_in_file(self, data):
        with open(CLIENT_FILE, 'a') as f:
            clients_list = read_users_from_file()

            rec_data = data

            if not rec_data:
                return False, 'auer' + my_address + '+++' + 'Something went wrong. Please, try again\n'

            credentials = rec_data.split()

            if len(credentials) < 2:
                return False, 'auer' + my_address + '+++' + 'Something is missing. Please, try again\n'

            login, passwd = credentials

            if login in clients_list.keys():
                if clients_list[login] == passwd:
                    return True, 'auok' + my_address + '+++' + self.user_list()
                else:
                    return False, 'auer' + my_address + '+++' + 'Wrong password. Try again\n'
            else:
                append_user_to_file(f, login, passwd)
                return True, 'auok' + my_address + '+++' + self.user_list()

    def user_list(self):
        with open(CLIENT_FILE, 'r') as f:
            client_credentials_list = f.read()
            addresses = json.dumps(clients_names)
            return client_credentials_list + '+++' + addresses + '+++' + user_login

    def _run(self):
        while True:
            try:
                ready_to_read, ready_to_write, in_error = select.select([sys.stdin, my_socket], [], [])
            except socket.error:
                continue
            else:
                for sock in ready_to_read:
                    if sock == my_socket:
                        try:
                            client_socket, client_address = my_socket.accept()
                            print(client_socket, client_address)
                        except socket.error:
                            break
                        else:
                            self._receive(client_socket)
                            client_socket.close()
                    else:
                        command = sys.stdin.readline()
                        sys.stdout.flush()
                        self.input_handler(command[-2:-1])

    def _receive(self, sock):
        msg_len = sock.recv(RECV_MSG_LEN)

        if len(msg_len) == RECV_MSG_LEN:
            msg_len = struct.unpack('>I', msg_len)[0]
            tot_data_len = 0

            sock.recv(2)
            command = sock.recv(8).decode('utf-16')

            addr, data = receive_message(sock, msg_len - 8, tot_data_len + 8)

            if addr != '':
                if command == 'auth':
                    self.auth_request(addr, data)
                elif command == 'auok':
                    self.auok_request(addr, data)
                elif command == 'auer':
                    self.auer_request(data)
                elif command == 'newu':
                    self.new_user_request(addr, data)
                elif command == 'quit':
                    self.quit_request(addr, data)
                elif command == 'mesg':
                    self.message_request(addr, data)
                elif command == 'stck':
                    self.sticker_request(addr, data)
                elif command == 'erro':
                    self.error_request(data)
                else:
                    self.wrong_command_request(addr)

    def input_handler(self, command):
        if command != '':
            if command == 'q':  # Exit from chat
                stop()
            elif command == 'm':  # Send a message
                msg = open_editor()
                if len(msg):
                    print_to_console('Me: ' + msg + '\n')
                    broadcast('', 'mesg' + my_address + '+++' + msg + '\n')

            elif command == 's':  # Send a sticker
                sticker = self.select_sticker()
                if len(sticker) != 0:
                    if sticker == '-':
                        print_to_console('No such sticker. Try again\n')
                    else:
                        print_to_console('Me:\n' + self.stickers[sticker] + '\n')
                        broadcast('', 'stck' + my_address + '+++' + sticker)
            else:
                print_to_console('Wrong command\n')

    def auth_request(self, addr, data):
        res = self.check_in_file(data)
        send(addr, res[1])

    def auok_request(self, addr, data):
        if data == '':
            stop()

        global clients_names
        user_data = data.split('+++')
        if len(user_data) == 3:
            try:
                clients_names = json.loads(user_data[1])
            except json.decoder.JSONDecodeError:
                stop()
            else:
                clients_names[addr] = user_data[2]
                with open(CLIENT_FILE, 'w') as f:
                    f.write(user_data[0])

                msg = 'newu' + my_address + '+++' + user_login + ' ' + user_pass

                broadcast('', msg)
                print_to_console('Welcome! Have a good day in chat =)\n')

    def auer_request(self, data):
        print_to_console(data, False)
        self.authorize()

    def new_user_request(self, addr, data):
        if data != '':
            info = data.split()
            if len(info) == 2:
                login = info[0]
                passwd = info[1]

                add_client(addr, login, passwd)

                if login == user_login:
                    msg = 'You have entered the chat once more from (%s)\n' % addr
                else:
                    msg = 'User ' + login + ' entered the chat room\n'
                print_to_console(msg, True)

    def quit_request(self, addr, login):
        if login != '':
            msg = 'User ' + login + ' left us\n'
            print_to_console(msg)

            remove_client(addr)

    def message_request(self, addr, data):
        if data and addr in clients_names:
            login = clients_names[addr]

            msg = login + ': ' + data
            print_to_console(msg)

    def sticker_request(self, addr, sticker_name):
        if sticker_name and addr in clients_names:
            login = clients_names[addr]

            msg = "\n" + self.stickers[sticker_name] if sticker_name in self.stickers.keys() else sticker_name

            print_to_console(login + ": " + msg + '\n')

    def error_request(self, data):
        print_to_console(data)

    def wrong_command_request(self, addr):
        send(addr, 'erro' + my_address + '+++' + 'Something went wrong. Try again\n')

    def select_sticker(self):
        with open('sticker.info') as initial:
            initial_message = initial.read()

        with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
            tf.write(initial_message.encode())
            tf.flush()
            subprocess.call([EDITOR, tf.name])

            tf.seek(0)

            with open(tf.name) as tmp:
                message = tmp.read()
                parts = message.split(':', 2)

                if len(parts) > 1:
                    sticker = ":" + parts[1] + ":"

                    if sticker in self.stickers.keys():
                        return sticker

                return '-'


def main():

    while True:
        host, port = get_connection_info()

        chat = WarningClient(host, port)
        chat.start()
        break


if __name__ == '__main__':
    main()
