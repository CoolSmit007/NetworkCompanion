import socket
import select
import queue
import logging
import threading as th
class socketClass:
    __logger = logging.getLogger()
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
                select.select([self.socket.fileno()],[],[])
                recieve_data+=self.socket.recv(1024)
                if not recieve_data:
                    self.closeSocket()
                    return
                if(len(recieve_data)>=1024):
                    self.receiveQueue.put(recieve_data[:1024])
                    recieve_data=recieve_data[1024:]
            except ValueError as error:
                self.__logger.error("Value error while receiving data: %s",str(error))
            except OSError as error:
                self.__logger.error("OS error while receiving data: %s",str(error))
                
    def connect(self,ip,port):
        try:
            self.socket.connect((ip,port))
            return True
        except ConnectionRefusedError as error:
            self.__logger.error("Connection refused error: %s",str(error))
            return False
        except TimeoutError as error:
            self.__logger.error("Timeout error while trying to connect: %s",str(error))
            return False 
        except OSError as error:
            self.__logger.error("OS error while trying to connect: %s",str(error))
            return False
           
    def startReceiveThread(self):
        self.receiveThread=th.Thread(target=self.receiveData)
        self.receiveThread.start()
        
    def closeSocket(self):
        self.__receiveLock.clear()
        self.receiveThread.join(timeout=1000)
        if(self.receiveThread.is_alive()):
            return False
        self.socket.close()
        return True