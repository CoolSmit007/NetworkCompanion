from backend.Socket import socketClass
import socket
from log_init import LOGGER
import threading as th
import select

class serverSocketClass:
    __waitingConnectionLock = th.Event()
    waitingConnectionThread = None
    
    def __init__(self):
        self.serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.__waitingConnectionLock.set()
        
    def listen(self,ip,port):
        self.serverSocket.bind((ip,port))
        self.serverSocket.listen(1)
        
    def awaitConnection(self,callbackFunction):
        while self.__waitingConnectionLock.is_set():
            try:
                ready, _, _ = select.select([self.serverSocket], [], [], 1.0)
                if ready:
                    skt, incoming_addr=self.serverSocket.accept()
                    callbackFunction(socketClass(skt,incoming_addr[0],incoming_addr[1]))
                    self.__waitingConnectionLock.clear()
            except OSError as error:
                LOGGER.error("Os error occured while waiting for connection %s",str(error))
                return
            except TimeoutError:
                pass
            
    def startWaitingConnectionThread(self,callbackFunction):
        self.__waitingConnectionLock.set()
        self.waitingConnectionThread = th.Thread(target=self.awaitConnection,args=(callbackFunction,))
        self.waitingConnectionThread.start()
        
    def stopWaitingConnectionThread(self):
        self.__waitingConnectionLock.clear()
        if(self.waitingConnectionThread):
            self.waitingConnectionThread.join(10.0)
            if(self.waitingConnectionThread.is_alive()):
                return False
        return True
        
    def closeServer(self):
        if(self.stopWaitingConnectionThread()):
            self.serverSocket.close()
            return True
        return False