import socket
import common

MY_PORT = 13000
DEST_PORT = 12000
BUFFER_SIZE = 2**(11) #32kb
TIMER_LIMIT = 100
STATE = 2

server_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
server_socket.bind(("127.0.0.1",MY_PORT))
print("Server ready to recieve")
data_feeder = common.Data_Feeder("base_first_reciever.png",300)
data_saver = common.Data_Saver("first_reciever_recieved.jpg")
client_adress = ("127.0.0.1",DEST_PORT)

#esse espera a conexao ser iniciada pela outra parte
common.Rdt(server_socket,data_feeder,data_saver,False,client_adress,TIMER_LIMIT,BUFFER_SIZE).transmit()