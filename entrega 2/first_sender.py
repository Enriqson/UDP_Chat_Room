import socket
import common

MY_PORT = 12000
DEST_PORT = 13000
BUFFER_SIZE = 2**(11) #1kb
TIMER_LIMIT = 100
STATE = 1

server_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
server_socket.bind(("127.0.0.1",MY_PORT))
print("Server ready to recieve")
data_feeder = common.Data_Feeder("base_first_sender.jpg",300)
data_saver = common.Data_Saver("first_sender_recieved.png")
client_adress = ("127.0.0.1",DEST_PORT)

#esse inicia a conexão
common.Rdt(server_socket,data_feeder,data_saver,True,client_adress,TIMER_LIMIT,BUFFER_SIZE).transmit()