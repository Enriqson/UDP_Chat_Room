# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import common
from threading import Thread,Lock
import time


# %%
SERVER_IP = '127.0.0.1'
SERVER_PORT = 12000
BUFFER_SIZE = 2**(10+5) #32kb
RESPONSE_TIME_LIMIT = 10
INPUT_TIME_LIMIT = 5

BASE_CLIENT_ADRESS = 13000
client_port = BASE_CLIENT_ADRESS


# %%
input_value=""
print("Digite seu nome para se conectar ao servidor")
input_value = input("hi, meu nome eh\n")

client_socket=None
while not client_socket:
    try:
        client_socket = common.RDT_client(client_port=client_port,server_adress=(SERVER_IP,SERVER_PORT),timer_limit=10,buffer_size=BUFFER_SIZE)
    except: client_port+=1000
client_socket.connect_to_server(input_value)


# %%
finished=False
lock = Lock()


# %%
def receive_msg():
    i =0
    while not finished:
        lock.acquire()
        message = client_socket.receive()

        if not message: i+=1
        else: i=0
        if i>5:
            globals()['finished']=True

        while message:
            print(message, flush=True)
            message = client_socket.receive()

        lock.release()
        
        time.sleep(0.2)

def get_input():
    while not finished:
        input_value =""
        try:
            input_value =input("")
            print("\033[A                             \033[A")
        except EOFError: pass
        if input_value: 
            lock.acquire()
            client_socket.send(input_value)
            lock.release()
            if input_value=='bye': globals()['finished']=True


# %%
message = client_socket.receive()
print(message, flush=True)

user_input_thread = Thread(target=get_input)
input_timer_thread = Thread(target=receive_msg)
user_input_thread.start()
input_timer_thread.start()


