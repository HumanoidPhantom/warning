import socket
import threading
import struct
import select
import os
import subprocess
import tempfile
import sys
import hashlib
import string
import atexit

LOGFILE = None

COMMANDS = [
    'mesg',
    'quit',
    'list',
    'auth',
    'auok',
    'auer'
]

DEF_MESSAGE = '[m - send message, s - stickers, q - quit]\n'

user_login = ''
curr_socket = None
running = True


def send(sock, msg):
    msg = struct.pack('>I', len(msg)) + msg.encode()
    sock.send(msg)


def stop():
    print('Disconnected from chat server')
    global running
    running = False
    if curr_socket:
        curr_socket.close()
    sys.exit()


def exit_handler():
    global curr_socket
    if curr_socket:
        send(curr_socket, 'quit' + user_login)
    stop()

atexit.register(exit_handler)


class ChatClient(threading.Thread):
    EDITOR = os.environ.get('EDITOR') if os.environ.get('EDITOR') else 'vim'

    def __init__(self, host, port, max_connections, recv_buffer, recv_msg_len):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.connections = []
        self.max_connections_number = max_connections
        self.recv_buffer = recv_buffer
        self.recv_msg_len = recv_msg_len
        self.login = ''

    def _socket_init(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        global curr_socket
        curr_socket = self.client_socket
        self.client_socket.settimeout(2)
        try:
            self.client_socket.connect((self.host, self.port))
        except socket.error:
            print("Unable to connect, sorry")
            sys.exit()

        self.connections = [sys.stdin, self.client_socket]

        print('Connected to chat.')

    def authorize(self):
        u_allowed_chars = 'A-Za-z0-9'+string.punctuation

        login = self.data_checker('Login (allowed: [' + u_allowed_chars + '], [exit] to leave): ', 1)
        passwd = self.data_checker('Password (at least 5 chars, allowed: [' + u_allowed_chars + '] [exit] to leave): ', 5)

        hpasswd = hashlib.sha256(passwd.encode()).hexdigest()

        header = "auth"
        global user_login
        user_login = login
        send(self.client_socket, header + login + " " + hpasswd)

    def data_checker(self, msg, min_len):
        allowed_chars = string.ascii_letters + string.digits + string.punctuation
        while True:
            inp_data = input(msg)

            if inp_data == 'exit':
                stop()
            elif len(inp_data) < min_len:
                print('Too short answer. Try again.')
                continue

            good_pass = True
            for ch in inp_data:
                if ch not in allowed_chars:
                    print('Restricted symbols were used')
                    good_pass = False
                    break

            if not good_pass:
                continue

            return inp_data

    def _run(self):
        while running:
            try:
                ready_to_read, ready_to_write, in_error = select.select(self.connections, [], [])
            except socket.error:
                continue
            else:
                for sock in ready_to_read:
                    if sock == self.client_socket:
                        self.receive(sock)
                    else:
                        command = sys.stdin.readline()

                        sys.stdout.flush()
                        command = command[-2:-1]
                        if command == 'q':
                            send(self.client_socket, 'quit'+self.login)
                            stop()
                        elif command == 'm':
                            msg = self.open_editor()
                            if len(msg):
                                msg = 'mesg' + msg
                                msg = struct.pack('>I', len(msg)) + msg.encode()
                                self.client_socket.send(msg)

                            sys.stdout.write(DEF_MESSAGE)
                            sys.stdout.flush()
                        # try:
                        #     data = self._receive(sock)
                        #     if data:
                        #         self._broadcast(sock, "\n" + '<' + str(sock.getpeername()) + '> ' + data)
                        # except error:
                        #     self._broadcast(sock, "\nClient (%s, %s) is offline\n" % (client_address[0],
                        # client_address[1]))
                        #     print("Client (%s, %s) is now offline\n" % (client_address[0], client_address[1]))
                        #     sock.close()
                        #     self.clients.remove(sock)
                        #     continue
        stop()

    def run(self):
        self._socket_init()
        self.authorize()
        self._run()

    def open_editor(self):
        with open('initial.txt') as initial:
            initial_message = initial.read()

        with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
            tf.write(initial_message.encode())
            tf.flush()
            subprocess.call([self.EDITOR, tf.name])

            tf.seek(0)

            with open(tf.name) as tmp:
                message = tmp.read().splitlines()

            res_message = ''
            for line in message:
                if not (len(line) > 3 and line[:3] == '###'):
                    res_message += ('\n' if len(res_message) else '') + line

            return res_message

    def receive(self, req_sock):
        res_data = None

        msg_len = req_sock.recv(self.recv_msg_len)
        if len(msg_len) == 4:
            res_data = ''
            msg_len = struct.unpack('>I', msg_len)[0]
            tot_data_len = 0

            command = req_sock.recv(4).decode()
            if command in COMMANDS:
                data = self.receive_message(req_sock, msg_len - 4, tot_data_len + 4)
                sys.stdout.write(data)
                if command == 'auer':
                    self.authorize()
                    return
                if command == 'mesg':
                    return
                else:
                    sys.stdout.write(DEF_MESSAGE)
                    sys.stdout.flush()
            else:
                sys.stdout.write('Something went wrong\n')
                sys.stdout.write(DEF_MESSAGE)
                sys.stdout.flush()

        else:
            stop()

    def receive_message(self, sock, msg_len, tot_data_len):
        data = ''

        while tot_data_len < msg_len:
            chunk = sock.recv(self.recv_buffer)
            if not chunk:
                data = None
                break
            else:
                data += str(chunk.decode())
                tot_data_len += len(chunk)

        return data


