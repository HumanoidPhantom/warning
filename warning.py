import sys
import server
import client
import socket

TYPE = 'client'
MAX_CONNECTIONS_NUMBER = 10
RECV_BUFFER = 4048
RECV_MSG_LEN = 4


def get_additional_info(port_not_null=False):

    while True:
        message = "Host/IP-address ("
        if not port_not_null:
            curr_ip = socket.gethostbyname(socket.gethostname())
            message += "your current IP-address [" + curr_ip + "]"
        message += "print [back] to change type): "

        host = input(message)
        if host == 'back':
            return -1, -1
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
            elif not port.isdigit() or int(port) < 0 or int(port) > 65535 or (port_not_null and port == 0):
                print('\nWrong value')
                continue
            else:
                break

        if host == -1:
            continue

        return host, int(port)


def main():

    while True:
        serv_type = input("Service to run: server/client ([exit] to leave): ")

        if serv_type == 'server':

            host, port = get_additional_info()
            if host == -1:
                continue

            chat_server = server.ChatServer(host, port, MAX_CONNECTIONS_NUMBER, RECV_BUFFER, RECV_MSG_LEN)
            chat_server.start()
            break
        elif serv_type == 'client':
            host, port = get_additional_info(True)
            chat_client = client.ChatClient(host, port, MAX_CONNECTIONS_NUMBER, RECV_BUFFER, RECV_MSG_LEN)
            chat_client.start()
            break
        elif serv_type == 'exit':
            print('Bye-bye!')
            sys.exit()
        else:
            print('Wrong value')


if __name__ == '__main__':
    main()
