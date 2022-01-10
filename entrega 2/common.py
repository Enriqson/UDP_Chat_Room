import time
import hashlib
import warnings

class Timer:
    def __init__(self):
        self._start_time = None

    #starta ou restarta o timer
    def restart(self):
        self._start_time = time.perf_counter()

    #checa o tempo decorrido desde que foi resetado
    def check(self):
        if self._start_time is None:
            raise Exception(f"Timer is not running. Use .restart() to start it")

        elapsed_time = time.perf_counter() - self._start_time
        return elapsed_time

#controlador pra ler dados de um arquivo
class Data_Feeder:
    def __init__(self,filename,buffer_size):
        self.file = open(filename,'rb')
        self.buffer_size = buffer_size
        self.data = None
        self.finished = False

    #retorna os dados lidos do arquivo
    def get_data(self):
        return self.data

    #carrega proximo chunck de dados 
    def load_next_data(self):
        if not self.finished:
            self.data = self.file.read(self.buffer_size)
            if self.data==b'': 
                self.finished = True
                self.file.close()


#controlador pra salvar os dados recebidos
class Data_Saver:
    def __init__(self,filename):
        self.file = open(filename,'wb')

    def save_data(self,data):
        self.file.write(data)

    def close(self):
        self.file.close()




class Rdt:
    def __init__(self,socket, data_feeder,data_saver,first_sender,client_adress,timer_limit,buffer_size):

        self.socket = socket
        self.data_saver = data_saver
        self.data_feeder = data_feeder
        self.timer_limit = timer_limit
        self.buffer_size = buffer_size
        self.client_adress = client_adress
        
        self.timer = Timer()
        #variavel de controle de loop para sabermos quando a transmissao de dados foi encerrada
        self.running = True        
        #seq pra saber qual foi o ultimo pacote enviado para a outra parte
        self.sender_seq = 0
        #ack para saber qual foi o ultimo pacote recebido da outra parte
        self.reciever_ack = 0
        #variavel pra checar se ocorreu um erro e será necessária retransmissão de dados
        self.retransmit = False

        #configura o estado inicial 
        if first_sender:
            self.state = 1
            self.data_feeder.load_next_data()
        else: self.state = 2

    
    #codifica e decodifica o header do protocolo 
    @staticmethod
    #importante notar o uso de eval, caso o protocolo fosse usado em várias linguagens diferentes seria necessário
    #transformar o header para json e a codificação dos dados para base64
    def decode_msg(bytecode):
        header_string = bytecode.decode('utf-8')
        decoded_msg = eval(header_string)
        return decoded_msg
    @staticmethod
    def encode_msg(msg):
        header_string = str(msg)
        bytecode = header_string.encode('utf-8')
        return bytecode

    #realiza o hashing de uma string de bytes
    @staticmethod
    def checksum(data):
        return hashlib.md5(data).hexdigest()

    #realiza o envio da mensagem via udp
    def send(self,msg):
        self.socket.sendto(msg,self.client_adress)
        self.timer.restart()
        self.state = 2

    #funcao que checa pela resposta da outra parte
    def recieve_response(self):
        #checa estouro de timer
        if self.timer._start_time==None or self.timer.check()<self.timer_limit:
            #checa se resposta chegou
            encoded_response,self.client_adress = self.socket.recvfrom(self.buffer_size)
            if(encoded_response):
                #desempacota o header
                self.last_response = self.decode_msg(encoded_response)
                #checa checksum dos dados
                if self.last_response["checksum"]!=self.checksum(self.last_response["data"]):
                    warnings.warn("pacote recebido com checksum invalido")
                else:
                    #caso pacote de dados esteja integro atualiza o ack que será retornado
                    self.reciever_ack = self.last_response["seq"]
                    #se o arquivo recebido ainda não foi finalizado salva os dados
                    if not self.last_response['finished_file_transmission']:
                        self.data_saver.save_data(self.last_response["data"])
                    else: 
                        #se a transmissao dos 2 arquivos foi finalizada e a outra parte recebeu os dados com sucesso
                        #finaliza a conexão
                        if self.data_feeder.finished and self.last_response["ack"]==self.sender_seq: 
                            self.running = False

                #checa se os dados foram recebidos corretamente pela outra parte
                if self.last_response["ack"]!=self.sender_seq:
                    self.retransmit = True
                    warnings.warn("outra parte não recebeu o ultimo pacote enviado corretamente")
                else:
                    #se deu tudo certo atualiza o seq e carrega novos dados
                    self.retransmit = False
                    self.sender_seq = 1 if self.sender_seq==0 else 0 
                    self.data_feeder.load_next_data()
                        
                self.state = 1
            else:
                self.state = 2    
        else:
            self.retransmit = True
            self.state=1
    
    #efetua a transmissão segura dos dados
    def transmit(self):
        while self.running:
            #estado de envio de dados
            if self.state==1:
                #le os dados do data_feeder, cria o header e o encoda para ser mandado através do udp
                data_to_send = self.data_feeder.get_data()
                msg = {
                    "ack":self.reciever_ack,
                    "seq":self.sender_seq,
                    "checksum":self.checksum(data_to_send),
                    "finished_file_transmission":self.data_feeder.finished,
                    "data":data_to_send
                }
                encoded_msg = self.encode_msg(msg)
                self.send(encoded_msg)
                #checa se nosso arquivo já terminou de ser enviado e se a outra parte tambem terminou
                if hasattr(self,'last_response') and self.data_feeder.finished and self.last_response['finished_file_transmission'] and not self.retransmit: 
                     self.running = False
            #estado de espera da resposta
            elif self.state == 2:
                self.recieve_response()
        #fecha o arquivo do data_saver
        self.data_saver.close()
        self.socket.close()