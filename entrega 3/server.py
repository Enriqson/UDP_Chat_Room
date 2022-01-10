# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import common


# %%
SERVER_PORT = 12000
BUFFER_SIZE = 2**(10+5) #32kb


# %%
server_socket = common.RDT_SERVER(server_adress=("127.0.0.1",SERVER_PORT),timer_limit=10,buffer_size=BUFFER_SIZE)


# %%
server_socket.start()


