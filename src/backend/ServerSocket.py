from Socket import socketClass
import socket
import logging
import threading as th

class serverSocketClass:
    __logger = logging.getLogger()
    __waitingConnectionLock = th.Event()
    waitingConnectionThread = None
    
    def __init__(self):
        self.serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.serverSocket.settimeout(60.0)
        self.__waitingConnectionLock.set()
        
    def listen(self,ip,port):
        self.serverSocket.bind((ip,port))
        self.serverSocket.listen(1)
        self.__waitingConnectionLock.set()
        
    def awaitConnection(self,callbackFunction):
        while self.__waitingConnectionLock.is_set():
            try:
                skt, incoming_addr=self.serverSocket.accept()
                skt.setblocking(True)
                callbackFunction(socketClass(skt,incoming_addr[0],incoming_addr[1]))
            except OSError as error:
                self.__logger.error("Os error occured while waiting for connection %s",str(error))
                return
            except TimeoutError:
                pass
            
    def startWaitingConnectionThread(self,callbackFunction):
        self.waitingConnectionThread = th.Thread(target=self.awaitConnection,args=(callbackFunction))
        self.waitingConnectionThread.start()
        
    def closeSocket(self):
        self.__waitingConnectionLock.clear()
        self.serverSocket.close()