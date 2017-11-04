import socket
import threading
import struct
import select
import sys
import os
import atexit

clients = []
lastMessages = []

LOGFILE = None
CLIENT_FILE = 'files/client.list'
LIST_MESSAGE = '[back] - return to server logs. [remove ip port] - disconnect user'
DEF_MESSAGE = '[m - send message, s - stickers, q - quit]\n'

user_login = ''
curr_socket = None
running = True

COMMANDS = [
    'mesg',
    'quit',
    'list',
    'auth',
    'auok',
    'auer',
    'erro',
    'stck',
]


class ChatServer(threading.Thread):





    def sticker(self, sock, sticker):
        if sticker in self.stickers.keys():
            user_addr = "('%s', %s)" % (sock.getpeername()[0], sock.getpeername()[1])
            username = self.clients_names[user_addr] + ':' \
                if user_addr in self.clients_names and self.clients_names[user_addr] != 'not logged in' \
                else ''
            return 'mesg' + username + '\n' + self.stickers[sticker], '', username + ' ' + sticker

        return '', 'erro' + 'Sticker not found', ''

    def auth_client(self, sock, data):
        with open(CLIENT_FILE, 'a') as f:
            read_clients = open(CLIENT_FILE, 'r')

            line_clients = read_clients.read().splitlines()

            clients_list = {}
            for client in line_clients:
                tmp = client.split()
                clients_list[tmp[0]] = tmp[1]

            read_clients.close()

            rec_data = data

            if not rec_data:
                return '', 'auer' + 'Something went wrong. Please, try again\n', ''

            credentials = rec_data.split()

            if len(credentials) < 2:
                return '', 'auer' + 'Something is missing. Please, try again\n', ''

            login, passwd = credentials

            if login in clients_list.keys():
                if clients_list[login] == passwd:
                    self.clients_active.append(sock)
                    addr = "('%s', %s)" % (sock.getpeername()[0], sock.getpeername()[1])
                    self.clients_names[addr] = login
                    return 'mesg' + 'User ' + login + ' entered the chat room\n', \
                           'auok' + self.stickers_text,\
                           'User ' + login + ' entered the chat room\n',
                else:
                    return '', 'auer' + 'Wrong password. Try again\n', ''
            else:
                new_client = login + ' ' + passwd + '\n'
                f.write(new_client)
                self.clients_active.append(sock)
                addr = "('%s', %s)" % (sock.getpeername()[0], sock.getpeername()[1])
                self.clients_names[addr] = login
                return 'mesg' + 'User ' + login + ' entered the chat room\n', \
                       'auok' + self.stickers_text, \
                       'User ' + login + ' entered the chat room\n',

    def _broadcast(self, sock, msg):
        for connection in self.clients_active:
            not_msg_author = connection != sock

            if not_msg_author:
                try:
                    self._send(connection, msg)
                except socket.error:
                    connection.close()
                    self.remove_client(connection)

    def remove_client(self, connection):
        if connection in self.clients:
            self.clients.remove(connection)

        if connection in self.clients_active:
            self.clients_active.remove(connection)

        addr = "('%s', %s)" % (connection.getpeername()[0], connection.getpeername()[1])

        if addr in self.clients_names:
            del self.clients_names[addr]

        try:
            connection.close()
        except socket.error:
            pass

    def _run(self):
        while self.running:
            try:
                ready_to_read, ready_to_write, in_error = select.select(self.clients, [], [])
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
                            addr = "('%s', %s)" % (client_socket.getpeername()[0], client_socket.getpeername()[1])
                            self.clients_names[addr] = 'not logged in'

                            self.print_to_console("Client (%s, %s) has connected\n" % (client_address[0],
                                                                                       client_address[1]))

                    elif sock != sys.stdin:
                        try:
                            broadcast, usr_answ, serv = self._receive(sock)

                            if broadcast != '':
                                self._broadcast(sock, broadcast)

                            if usr_answ != '':
                                self._send(sock, usr_answ)

                            if serv != '':
                                self.print_to_console(serv)

                        except socket.error:
                            self._broadcast(sock, "\nClient (%s, %s) is offline\n" % (client_address[0],
                                                                                      client_address[1]))
                            self.print_to_console("Client (%s, %s) is now offline\n" % (client_address[0],
                                                                                            client_address[1]))
                            sock.close()
                            self.clients.remove(sock)
                            continue
                    else:
                        command = sys.stdin.readline()

                        sys.stdout.flush()

                        if self.show_income:
                            command = command[-2:-1]
                            if command == 'q':
                                self.stop()
                            elif command == 'l':
                                self.show_income = False
                                self.list_clients()
                        else:
                            command = command.split()
                            if len(command) != 0:
                                if command[0] == 'back':
                                    self.show_income = True
                                    self.print_to_console(DEF_MESSAGE, False)
                                elif command[0] == 'remove' and not len(command) < 3 and len(self.clients_names) != 0:
                                    self.remove_client_command(command)
                                else:
                                    print('No such command. [back] - return to server logs. [remove ip port] - '
                                          'disconnect user (if there is user)')

                                    sys.stdout.flush()
                            else:
                                print('No such command. [back] - return to server logs. [remove ip port] - '
                                      'disconnect user (if there is user)')

                                sys.stdout.flush()
        self.stop()

    def remove_client_command(self, command):
        rec_addr = "('%s', %s)" % (command[1], command[2])
        for find_sock in self.clients:
            if find_sock != self.server_socket and find_sock != sys.stdin:
                peername = "('%s', %s)" % (find_sock.getpeername()[0], find_sock.getpeername()[1])
                if rec_addr == peername:
                    username = ''
                    if rec_addr in self.clients_names.keys():
                        username = self.clients_names[rec_addr] + ' ' \
                            if self.clients_names[rec_addr] != 'not logged in' \
                            else rec_addr + ' '

                    resp_msg = 'User ' + username + 'was removed from chat'

                    self._broadcast(find_sock, 'mesg' + resp_msg + '\n')
                    self.remove_client(find_sock)

                    self.show_income = True
                    self.print_to_console(resp_msg)

        if not self.show_income:
            self.print_to_console("User was'n found. Try again", False)
            self.list_clients()

    def print_to_console(self, msg, with_default = True):
        if self.show_income:
            print(msg)
        if with_default:
            print(DEF_MESSAGE)
        sys.stdout.flush()

    def list_clients(self):
        if len(self.clients_names.items()) == 0:
            print('There are no clients now')
            print('[back] - return to server logs.')
        else:

            for addr, login in dict(self.clients_names).items():
                print("%s %s" % (login, addr))

            print('[back] - return to server logs. [remove ip port] - disconnect user')

        sys.stdout.flush()
