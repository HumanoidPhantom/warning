import socket
import threading
import struct
import select
import sys

clients = []
lastMessages = []

PORT = 9090
HOST = "127.0.0.1"
LOGFILE = None

COMMANDS = [
    'answer',
    'history',
    'quit',
    'list'
]


class ChatServer(threading.Thread):

    def __init__(self, host, port, max_connections, recv_buffer, recv_msg_len):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.clients = []
        self.running = True
        self.max_connections_number = max_connections
        self.recv_buffer = recv_buffer
        self.recv_msg_len = recv_msg_len

    def _bind_socket(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
        except socket.error as msg:
            print('Something went wrong: ', msg)
            sys.exit()

        print('Server has been started: ', self.server_socket.getsockname())
        self.server_socket.listen(self.max_connections_number)
        self.clients.append(self.server_socket)

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

        for connection in self.clients:
            not_server = connection != self.server_socket
            not_msg_author = connection != sock

            if not_msg_author and not_server:
                try:
                    self._send(connection, msg)
                except socket.error:
                    connection.close()
                    self.clients.remove(connection)

    def _run(self):
        while self.running:
            try:
                ready_to_read, ready_to_write, in_error = select.select(self.clients, [], [], 60)
            except socket.error:
                continue
            else:
                for sock in ready_to_read:

                    if sock == self.server_socket:
                        try:
                            client_socket, client_address = self.server_socket.accept()
                        except socket.error:
                            break
                        else:
                            self.clients.append(client_socket)
                            print("Client (%s, %s) has connected\n" % (client_address[0], client_address[1]))

                            self._broadcast(client_socket, "\n[%s:%s] entered the chat room\n" % (client_address[0],
                                                                                                  client_address[1]))
                    else:
                        try:
                            data = self._receive(sock)
                            if data:
                                self._broadcast(sock, "\n" + '<' + str(sock.getpeername()) + '> ' + data)
                        except socket.error:
                            self._broadcast(sock, "\nClient (%s, %s) is offline\n" % (client_address[0],
                                                                                      client_address[1]))
                            print("Client (%s, %s) is now offline\n" % (client_address[0], client_address[1]))
                            sock.close()
                            self.clients.remove(sock)
                            continue
        self.stop()

    def run(self):
        self._bind_socket()
        self._run()

    def stop(self):
        self.running = False
        self.server_socket.close()
