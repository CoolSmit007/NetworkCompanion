from backend.Socket import socketClass
from backend.ServerSocket import serverSocketClass
from models.DataTypeEnum import DataType

import queue
import threading as th
from log_init import LOGGER
import json

class connection:
    __receiveLock = th.Event()
    receiveThread=None
    def __init__(self):
        self.socket = socketClass()
        self.server = serverSocketClass()
        self.fileQueue = queue.Queue()
        self.folderQueue = queue.Queue()
        self.screenQueue = queue.Queue()
        self.audioQueue = queue.Queue()
        self.keyboardQueue = queue.Queue()
        self.mouseQueue = queue.Queue()
        
    def __receive(self):
        while self.__receiveLock.is_set():
            try:
                data = self.socket.receiveQueue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            if(not isinstance(data, bytes)):
                LOGGER.error("Data is not a bytearray")  
                continue
            
            try:
                decodedData = data.rstrip(b'\x00').decode()
            except UnicodeDecodeError as error:
                LOGGER.error("Unicode Decode error %s",error)  
                continue
            
            if(not decodedData[-1]=='\n'):
                LOGGER.error("Data doesn't contain \\n as the last character")  
                continue
            
            try:
                jsonData = json.loads(decodedData[:-1])
            except json.JSONDecodeError as error:
                LOGGER.error("JSON Decode error %s",error)  
                continue
            
            bytesDataLength = jsonData.get("data_length")
            paddedLength = jsonData.get("padding_length")
            typeOfData = jsonData.get("type")
            
            if not bytesDataLength:
                LOGGER.error("No attribute 'data_length' found in JSON")  
                continue
            
            if not paddedLength:
                LOGGER.error("No attribute 'padded_length' found in JSON")  
                continue
            
            if not typeOfData:
                LOGGER.error("No attribute 'type' found in JSON")  
                continue
                
            finalData=bytes()
            while bytesDataLength>len(finalData):
                finalData += self.socket.receiveQueue.get()
                
            if(bytesDataLength!=len(finalData)):
                LOGGER.error("JSON final bytes length doesn't match data_length, data_length=%d, len of final bytes=%d",bytesDataLength,len(finalData))  
                continue
            
            if not all(bytesValue==0 for bytesValue in finalData[-paddedLength:]):
                LOGGER.error("Not all padded bytes are null bytes for padding_length=%d",paddedLength)  
                continue
            
            finalData = finalData[:-paddedLength] if paddedLength > 0 else finalData
                
            match typeOfData:
                case DataType.COMMAND.value:
                    pass
                case DataType.AUDIO.value:
                    self.audioQueue.put(finalData)
                case DataType.SCREEN.value:
                    self.screenQueue.put(finalData)
                case DataType.FILE.value:
                    self.fileQueue.put(finalData)
                case DataType.FOLDER.value:
                    self.folderQueue.put(finalData)
                case DataType.KEYBOARD.value:
                    self.keyboardQueue.put(finalData)
                case DataType.MOUSE.value:
                    self.mouseQueue.put(finalData)
            
    def __startReceiveThread(self):
        self.__receiveLock.set()
        self.receiveThread=th.Thread(target=self.__receive)
        self.receiveThread.start()
        
    def __stopReceiveThread(self):
        self.__receiveLock.clear()
        if(self.receiveThread):
            self.receiveThread.join(timeout=10.0)
            if(self.receiveThread.is_alive()):
                return False
        return True
    
    def send(self,type,data):
        if not isinstance(data,bytes):
            LOGGER.error("Data is not of type bytes")  
            raise Exception("Data is not of type bytes")
        
        if not isinstance(type,DataType):
            LOGGER.error("Type is not an enum of type DataType")  
            raise Exception("Type is not an enum of type DataType")
        
        padLength = (1024-(len(data)%1024))%1024
        jsonData = {"type":type.value, "data_length":len(data)+padLength,"padding_length":padLength}
        encodedJSONData = (json.dumps(jsonData)+'\n').encode().ljust(1024, b'\x00')
        paddedData = data.ljust(len(data) + padLength, b'\x00')
        self.socket.sendData(encodedJSONData)
        self.socket.sendData(paddedData)
            
    def connect(self,ip,port):
        LOGGER.info("Connecting to ip:%s and port %d:",ip,port)
        self.socket.connect(ip,port)
        self.socket.startReceiveThread()
        self.__startReceiveThread()
    
    def acceptConnectionAndStartReceiveThread(self,socket):
        if not isinstance(socket,socketClass):
            LOGGER.error("Socket variabled is of class %s instead of socketClass",str(type(socket)))
            return
        LOGGER.info("Accepting connection from ip:%s and port %d:",socket.ip,socket.port)
        self.socket=socket 
        self.socket.startReceiveThread()
        self.__startReceiveThread()
        
    def startServer(self,ip,port,callbackFunction):
        LOGGER.info("Starting server bound to ip:%s and port %d:",ip,port)
        self.server.listen(ip,port)
        self.server.startWaitingConnectionThread(callbackFunction)
        
    def closeConnection(self):
        if(self.__stopReceiveThread()):
            socketClosed =  self.socket.closeSocket()
            serverClosed = self.server.closeServer()
            return socketClosed and serverClosed
        return False