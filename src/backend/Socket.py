import socket
import select
import queue
import threading as th

from log_init import LOGGER
class socketClass:
    __receiveLock = th.Event()
    receiveThread = None
    ip=None
    port=None
    def __init__(self, socketObject=None, ip=None, port=None):
        self.socket = socketObject if socketObject!=None else socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.ip=ip
        self.port=port
        self.receiveQueue = queue.Queue()
        self.__receiveLock.set()
        
    @staticmethod
    def getPersonalIp():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ans=s.getsockname()
        s.close()
        return ans[0]

    def sendData(self,data):
        select.select([],[self.socket.fileno()],[])
        self.socket.sendall(data)
        
    def receiveData(self):
        recieve_data=bytes()
        while self.__receiveLock.is_set():
            try:
                ready,_,_ = select.select([self.socket.fileno()],[],[],1.0)
                if ready:
                    recieve_data+=self.socket.recv(1024)
                    if not recieve_data:
                        self.closeSocket()
                        return
                    if(len(recieve_data)>=1024):
                        self.receiveQueue.put(recieve_data[:1024])
                        recieve_data=recieve_data[1024:]
            except ValueError as error:
                LOGGER.error("Value error while receiving data: %s",str(error))
            except OSError as error:
                LOGGER.error("OS error while receiving data: %s",str(error))
                
    def startReceiveThread(self):
        self.__receiveLock.set()
        self.receiveThread=th.Thread(target=self.receiveData)
        self.receiveThread.start()
        
    def stopReceiveThread(self):
        self.__receiveLock.clear()
        if(self.receiveThread):
            self.receiveThread.join(timeout=10.0)
            if(self.receiveThread.is_alive()):
                return False
        return True
    
    def connect(self,ip,port):
        try:
            self.socket.connect((ip,port))
            return True
        except ConnectionRefusedError as error:
            LOGGER.error("Connection refused error: %s",str(error))
            return False
        except TimeoutError as error:
            LOGGER.error("Timeout error while trying to connect: %s",str(error))
            return False 
        except OSError as error:
            LOGGER.error("OS error while trying to connect: %s",str(error))
            return False
        
    def closeSocket(self):
        if(self.stopReceiveThread()):
            self.socket.close()
            return True
        return False