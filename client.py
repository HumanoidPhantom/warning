import socket
import threading
import struct
import select
import os
import subprocess
import tempfile
import sys

LOGFILE = None

COMMANDS = [
    'answer',
    'history',
    'quit',
    'list'
]


class ChatClient(threading.Thread):
    EDITOR = os.environ.get('EDITOR') if os.environ.get('EDITOR') else 'vim'

    def __init__(self, host, port, max_connections, recv_buffer, recv_msg_len):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.connections = []
        self.running = True
        self.max_connections_number = max_connections
        self.recv_buffer = recv_buffer
        self.recv_msg_len = recv_msg_len

    def _socket_init(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(2)
        try:
            self.client_socket.connect((self.host, self.port))
        except socket.error:
            print("Unable to connect, sorry")
            sys.exit()

        self.connections = [sys.stdin, self.client_socket]

    def _send(self, sock, msg):
        msg = struct.pack('>I', len(msg)) + msg.encode()
        print(msg)
        sock.send(msg)

    def _receive(self, sock):
        data = None

        msg_len = sock.recv(self.recv_msg_len)

        if len(msg_len) == 4:
            data = ''
            msg_len = struct.unpack('>I', msg_len)[0]
            tot_data_len = 0

            while tot_data_len < msg_len:
                chunk = sock.recv(self.recv_buffer)
                if not chunk:
                    data = None
                    break
                else:
                    data += str(chunk.decode())
                    tot_data_len += len(chunk)

        return data

    def _broadcast(self, sock, msg):

        for connection in self.connections:
            not_server = connection != self.client_socket
            not_msg_author = connection != sock

            if not_msg_author and not_server:
                try:
                    self._send(connection, msg)
                except socket.error:
                    connection.close()
                    self.connections.remove(connection)

    def _run(self):
        while self.running:
            try:
                ready_to_read, ready_to_write, in_error = select.select(self.connections, [], [])
            except socket.error:
                continue
            else:
                for sock in ready_to_read:
                    if sock == self.client_socket:
                        self.receive(sock)
                    else:
                        msg = sys.stdin.readline()
                        msg = struct.pack('>I', len(msg)) + msg.encode()

                        sock.send(msg)
                        sys.stdout.write('[Me] ')
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
        self.stop()

    def run(self):
        self._socket_init()
        self._run()

    def stop(self):
        self.running = False
        self.client_socket.close()

    def open_vim(self):

        initial_message = ""

        with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
            tf.write(initial_message.encode())
            tf.flush()
            subprocess.call([self.EDITOR, tf.name])

            tf.seek(0)

            with open(tf.name) as tmp:
                message = tmp.read()

            return message

    def receive(self, req_sock):
        res_data = None

        msg_len = req_sock.recv(self.recv_msg_len)

        if len(msg_len) == 4:
            res_data = ''
            msg_len = struct.unpack('>I', msg_len)[0]
            tot_data_len = 0

            while tot_data_len < msg_len:
                chunk = req_sock.recv(self.recv_buffer)
                if not chunk:
                    res_data = None
                    break
                else:
                    res_data += str(chunk.decode())
                    tot_data_len += len(chunk)

            sys.stdout.write(res_data)
            sys.stdout.write('[Me] ')
            sys.stdout.flush()
        else:
            print('\nDisconnected from chat server')
            sys.exit()
