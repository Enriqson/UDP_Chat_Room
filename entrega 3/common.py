import warnings
import socket

#funcoes pra codificar e decodificar o cabecalho do protocolo
#transformar de objeto para bytecode
def decode_rdt_msg(bytecode):
    header_string = bytecode.decode('utf-8')
    decoded_msg = eval(header_string)
    return decoded_msg

def encode_rdt_msg(msg):
    header_string = str(msg)
    bytecode = header_string.encode('utf-8')
    return bytecode

#funcao que calcula o checksum de uma mensagem
def calc_checksum(data):
    if type(data)!=type(''): data = str(data)
    sum = 0
    for i in range(0,len(data),2):
        if i + 1 >= len(data):
            sum += ord(data[i]) & 0xFF
        else:
            w = ((ord(data[i]) << 8) & 0xFF00) + (ord(data[i+1]) & 0xFF)
            sum += w

    # take only 16 bits out of the 32 bit sum and add up the carries
    while (sum >> 16) > 0:
        sum = (sum & 0xFFFF) + (sum >> 16)

    # one's complement the result
    sum = ~sum

    return sum & 0xFFFF

class RDT_SERVER:
    def __init__(self,server_adress ,timer_limit,buffer_size):

        self.server_adress = server_adress
        self.timer_limit = timer_limit
        self.buffer_size = buffer_size
        self.client_list = {}
        self.message_buffer = []

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind(self.server_adress)

    #loop onde o servidor roda
    def start(self):
        print("Server ready to recieve", flush=True)
        while 1:
            #recebe mensagem e a resolve
            message,client_adress = self.receive()
            self.resolve_message(message,client_adress)

    #resolve a mensagem dependendo do tipo
    def resolve_message(self,message,client_adress):
        print("mensagem recebida:"+message, flush=True)
        if message:
            if client_adress in self.client_list.keys():
                if message =="bye":
                    print("Cliente pediu pra sair", flush=True)
                    self.remove_client(client_adress)
                elif message =="list":
                    print("Cliente pediu lista")
                    #manda apenas para o cliente que pediu a lista
                    client_list_str = "Lista de clientes:"
                    for client in self.client_list.values():
                        client_list_str+="\n"+client["NAME"]
                    self.send(client_list_str,client_adress)
                else:
                    print("cliente enviou a mensagem:" +message, flush=True)
                    client_name = self.client_list[client_adress]["NAME"]
                    self.broadcast(client_name+" :"+message)
            else:
                if message[:15] =="hi, meu nome eh":
                    name = message[16:]
                    print("Adicionando novo cliente "+ name, flush=True)
                    self.add_client(name,1,0,client_adress)   

    #funcao que adiciona cliente à lista de clientes e avisa aos demais clientes que o cliente foi includo
    def add_client(self,name,ack,seq,client_adress):
        self.client_list[client_adress] = {
            "NAME":name,
            "ACK":ack,
            "SEQ":seq
        }
        self.broadcast(name+" entrou no chat")

    #remove um cliente da lista de clientes e avisa aos demais clientes que o cliente foi excluido
    def remove_client(self,client_adress):
        client_name = self.client_list[client_adress]["NAME"]
        print("Removendo cliente "+client_name, flush=True)
        self.client_list.pop(client_adress, None)
        self.broadcast(client_name+" saiu do chat")

    #recebe o pacote
    def receive(self):
        #checa se nao tem um pacote esperando para ser processado, se não tiver espera pacote do cliente
        if len(self.message_buffer):
            message,client_adress = self.message_buffer.pop(0)
        else:
            packet,client_adress = self.server_socket.recvfrom(self.buffer_size)
            rdt_header = decode_rdt_msg(packet)
            message = self.check_packet(rdt_header,client_adress)
        return message,client_adress

    #checa as condições para o pacote ser valido
    def check_packet(self,rdt_header,client_adress):
        #print("Checando pacote novo", flush=True)
        print(rdt_header)
        if not rdt_header["IS_ACK"]:
            if rdt_header["CHECKSUM"]==calc_checksum(rdt_header["DATA"]):
                if client_adress in self.client_list.keys():
                    if rdt_header["ACK"] == self.client_list[client_adress]["SEQ"]:
                        self.client_list[client_adress]["ACK"] = rdt_header["SEQ"]+1
                        self.send_ack(rdt_header["SEQ"]+1,client_adress)
                        print("Recebi um pacote bunitinho que dizia: "+str(rdt_header), flush=True)
                        return rdt_header["DATA"]
                    elif rdt_header["SEQ"]<self.client_list[client_adress]["ACK"]:
                        print("pacote de dados já processado")
                        self.send_ack(rdt_header["SEQ"]+1,client_adress)
                        return ""
                    else:
                        print("Recebi pacote com Ack invalido", flush=True)
                        self.send_ack(0,client_adress)
                        return ""
                else:
                    return rdt_header["DATA"]
            else:
                print("Recebi um pacote com checksum inválido")
                self.send_ack(0,client_adress)
                return ""
        else: 
            print("Ack duplicado/inesperado")
            return ""

    def create_header(self,data,ack,is_ack,client_adress):
        checksum = calc_checksum(data)
        seq = self.client_list[client_adress]["SEQ"]
        return {
            "CHECKSUM":checksum,
            "SEQ":seq,
            "ACK":ack,
            "DATA":data,
            "IS_ACK":is_ack
        }

    def send_ack(self,ack_value,client_adress):
        #print("Mandando ack para: "+str(client_adress))
        header = self.create_header("",ack_value,True,client_adress)
        encoded_header = encode_rdt_msg(header)
        self.server_socket.sendto(encoded_header,client_adress)

    def send(self,data,destination_adress):
        #print("enviando "+str(data)+" pra"+ str(destination_adress))
        header = self.create_header(data,self.client_list[destination_adress]["ACK"],False,destination_adress)
        encoded_header = encode_rdt_msg(header)
        self.client_list[destination_adress]["SEQ"]+=1
        timeouts=0
        resend = True
        rcv_ack = 0
        while(rcv_ack!=self.client_list[destination_adress]["SEQ"]):
            if resend: self.server_socket.sendto(encoded_header,destination_adress)
            resend = True
            try:
                self.server_socket.settimeout(self.timer_limit)
                #print("esperando ack do cliente")
                packet,client_adress = self.server_socket.recvfrom(self.buffer_size)
                self.server_socket.settimeout(None)
                rdt_header = decode_rdt_msg(packet)
                if rdt_header["IS_ACK"]:
                    if rdt_header["CHECKSUM"]==calc_checksum(rdt_header["DATA"]):
                        rcv_ack = rdt_header["ACK"]
                        #print("resposta chegou bunitinho")
                        #print(rdt_header)
                else:
                    print("esperava ack mas chegou uma mensagem")
                    #caso o ack esperado tenha sido uma mensagem quer dizer que 
                    #o cliente não recebeu um ack do servidor
                    #checa o pacote, reenvia o ack perdido e resolve a mensagem
                    if client_adress==destination_adress:
                        if self.client_list[client_adress]["ACK"]> rdt_header["SEQ"]:
                            #print("ack do cliente não foi enviado, reenviando")
                            self.send_ack(rdt_header["SEQ"]+1,client_adress)
                    else:
                        #novo cliente mandou mensagem para o servidor antes que ele concluisse o envio a outro usuario
                        #checa o pacote, confirma recebimento para o cliente e salva a mensagem para ser processada depois
                        message = self.check_packet(rdt_header,client_adress)
                        if message:
                            self.message_buffer.append((rdt_header["DATA"],client_adress))

            except socket.timeout:
                timeouts+=1
                #print("cliente demorou dms")
                if timeouts>5:
                    #print("cliente deu muito timeout")
                    self.remove_client(destination_adress)
                    break
        self.server_socket.settimeout(None)


    def broadcast(self,data):
        #print("Fazendo broadcast")
        client_adresses = list(self.client_list.keys())
        for adress in client_adresses:
            self.send(data,adress)

class RDT_client:
    def __init__(self,client_port,server_adress ,timer_limit,buffer_size):

        self.server_adress = server_adress
        self.timer_limit = timer_limit
        self.buffer_size = buffer_size
        self.client_port = client_port
        self.ack=0
        self.seq=0

        self.message_buffer = []

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.bind(("127.0.0.1",self.client_port))

    def connect_to_server(self,name):
        self.send("hi, meu nome eh "+name)

    def create_header(self,data,ack,is_ack):
        checksum = calc_checksum(data)
        seq = self.seq
        return {
            "CHECKSUM":checksum,
            "SEQ":seq,
            "ACK":ack,
            "DATA":data,
            "IS_ACK":is_ack
        }
        
    def send(self,data):
        header = self.create_header(data,self.ack,False)
        encoded_header = encode_rdt_msg(header)
        self.seq+=1
        #print("mandando",data,flush=True)
        rcv_ack = 0

        try:
            while(rcv_ack!=self.seq):
                self.client_socket.sendto(encoded_header,self.server_adress)
                self.client_socket.settimeout(self.timer_limit)
                #print("esperando ack do server",self.seq, flush=True)
                packet,server_adress = self.client_socket.recvfrom(self.buffer_size)
                self.client_socket.settimeout(None)
                rdt_header = decode_rdt_msg(packet)
                #print("opa",rdt_header,flush=True)
                if not rdt_header["IS_ACK"]:
                    if rdt_header["CHECKSUM"]==calc_checksum(rdt_header["DATA"]):
                        #print("recebi um pacote inesperado mas vou colocar no buffer",flush=True)
                        self.ack = rdt_header["SEQ"]+1
                        self.send_ack(rdt_header["SEQ"]+1)
                        self.message_buffer.append(rdt_header["DATA"])
                    else: self.send_ack(0)
                    
                if rdt_header["CHECKSUM"]==calc_checksum(rdt_header["DATA"]):
                    rcv_ack = rdt_header["ACK"]
            #print("resposta chegou bunitinho")
        except socket.timeout:
            warnings.warn("Server timeout")
            exit(0)
        self.client_socket.settimeout(None)

    def receive(self):

        if len(self.message_buffer):
            #se tiver algo no buffer retorna a mensagem
            #print("tirando mensagem guardada no buffer",flush=True)
            return self.message_buffer.pop(0)
        try:
            #print("procurando mensagem nova do server")
            self.client_socket.settimeout(self.timer_limit)
            packet,server_adress = self.client_socket.recvfrom(self.buffer_size)
            #print(packet)
            self.client_socket.settimeout(None)

            rdt_header = decode_rdt_msg(packet)

            if not rdt_header["IS_ACK"]:
                if rdt_header["CHECKSUM"]==calc_checksum(rdt_header["DATA"]):
                    if rdt_header["ACK"] == self.seq:
                        self.ack = rdt_header["SEQ"]+1
                        self.send_ack(rdt_header["SEQ"]+1)
                        return rdt_header["DATA"]
                    else:
                        self.send_ack(0)
                        return ""
                else:
                    self.send_ack(0)
                    return ""
            else: 
                #ack duplicado
                return ""

        except socket.timeout:
            #print("nao achei nada")
            return ""

    def send_ack(self,ack_value):
        #print("Mandando ack", flush=True)
        header = self.create_header("",ack_value,True)
        encoded_header = encode_rdt_msg(header)
        self.client_socket.sendto(encoded_header,self.server_adress)