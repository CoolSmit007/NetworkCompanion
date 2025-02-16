from Socket import socketClass
import socket
import logging
import threading as th

class serverSocketClass:
    logger = logging.getLogger()
    waitingConnectionLock = th.Event()
    waitingConnectionThread = None
    
    def __init__(self):
        self.serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.serverSocket.settimeout(60.0)
        self.waitingConnectionLock.set()
        
    def listen(self,ip,port):
        self.serverSocket.bind((ip,port))
        self.serverSocket.listen(1)
        self.waitingConnectionLock.set()
        
    def awaitConnection(self,callbackFunction):
        while self.waitingConnectionLock.is_set():
            try:
                skt, incoming_addr=self.serverSocket.accept()
                skt.setblocking(True)
                callbackFunction(socketClass(skt,incoming_addr[0],incoming_addr[1]))
            except OSError as error:
                self.logger.error("Os error occured while waiting for connection %s",str(error))
                return
            except TimeoutError:
                pass
            
    def startWaitingConnectionThread(self,callbackFunction):
        self.waitingConnectionThread = th.Thread(target=self.awaitConnection,args=(callbackFunction))
        self.waitingConnectionThread.start()
        
    def closeSocket(self):
        self.waitingConnectionLock.clear()
        self.serverSocket.close()