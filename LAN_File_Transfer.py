import tkinter as tk
from tkinter import ttk
import os
from tkinter.filedialog import askopenfilename
import socket
import select
import threading as th
from tkinter import filedialog
import queue as Q
import shutil
def donothing():
    pass
def destroy(window):
    window.destroy()
    window.update()
# Globals
base=tk.Tk()
base.resizable(False,False)
base.title("Share Files on LAN")
connection_accepted=False
serverskt=None
skt=None
start_conn=None
start_disconnect=False
reciever_thread=None
sender_thread=None
sending_queue=Q.Queue()
reciever_queue=Q.Queue()
send_size=512 << 10
recieve_size=512 << 10
pendingconfirmation_label=None
popup_file=None
file_directory=None
filename_var=None
file=None
file_send_progressbar=None
percentage_label=None
filename=None
file_send_event=th.Event()
file_send_event.set()
ack_counter_send=0
folder_sending=False
# File Send Function
def file_send():    
    global file_send_progressbar,file_send_event,ack_counter_send,file_directory,folder_sending,file
    first_time=True
    if folder_sending:
        size=filename_var.get().split("\n")[1]
        size=int(size[1:-7])
        totalsize=size
        sent=0
        for path, dirs, files in os.walk(file_directory):
            for f in files:
                ack_counter_send=0
                fp = os.path.join(path, f)
                size=os.path.getsize(fp)
                file=open(fp,"rb")
                if first_time:
                    file_send_event.clear()
                    if len(path.split('\\',1))==1:
                        sending_queue.put("<<NODIR>>".encode())
                    else:
                        sending_queue.put(path.split('\\',1)[1].encode())
                    first_time=False
                else:
                    select.select([],[skt.fileno()],[])
                    if len(path.split('\\',1))==1:
                        skt.sendall("<<NODIR>>".encode())
                    else:
                        skt.sendall(path.split('\\',1)[1].encode())
                # print("Sent Directory")
                select.select([skt.fileno()],[],[])
                check_ack_recv=skt.recv(7)
                if check_ack_recv.decode()!="<<ACK>>":
                    print("error-"+check_ack_recv.decode())
                # print("Recieved ACK")
                select.select([],[skt.fileno()],[])
                skt.sendall((f+'\n('+str(size)+' Bytes)').encode())
                # print("Sent Filename")
                select.select([skt.fileno()],[],[])
                check_ack_recv=skt.recv(7)
                if check_ack_recv.decode()!="<<ACK>>":
                    print("error-"+check_ack_recv.decode())
                # print("Recieved ACK")
                while data:=file.read(send_size):
                    select.select([],[skt.fileno()],[])
                    skt.sendall(data)
                    ack_counter_send+=1
                    sent+=len(data)
                    file_send_progressbar['value']=int((sent/totalsize)*100)
                    percentage_label["text"]=str(int((sent/totalsize)*100))+"%"
                    if ack_counter_send==100:
                        select.select([skt.fileno()],[],[])
                        check_ack_recv=skt.recv(7)
                        if check_ack_recv.decode()!="<<ACK>>":
                            print("error-"+check_ack_recv.decode())
                        ack_counter_send=0
                select.select([],[skt.fileno()],[])
                skt.sendall("<<EOF>>".encode())
                # print("Sent EOF")
                select.select([skt.fileno()],[],[])
                check_ack_recv=skt.recv(7)
                if check_ack_recv.decode()!="<<ACK>>":
                    print("error-"+check_ack_recv.decode())
                # print("Recieved ACK")
                file.close()
        pendingconfirmation_label["text"]="Folder Sent"
        popup_file.protocol("WM_DELETE_WINDOW",lambda: destroy(popup_file))
        file_send_event.set()
    else:
        size=filename_var.get().split("\n")[1]
        size=int(size[1:-7])
        totalsize=size
        sent=0
        first_time=True
        ack_counter_send=0
        while data:=file.read(send_size):
            if first_time:
                file_send_event.clear()
                sending_queue.put(data)
                first_time=False
            else:
                select.select([],[skt.fileno()],[])
                skt.sendall(data)
            if ack_counter_send==100:
                select.select([skt.fileno()],[],[])
                check_ack_recv=skt.recv(7)
                if check_ack_recv.decode()!="<<ACK>>":
                    print("error-"+check_ack_recv.decode())
                ack_counter_send=0
            ack_counter_send+=1
            sent+=len(data)
            file_send_progressbar['value']=int((sent/totalsize)*100)
            percentage_label["text"]=str(int((sent/totalsize)*100))+"%"
        select.select([],[skt.fileno()],[])
        skt.sendall("<<EOF>>".encode())
        select.select([skt.fileno()],[],[])
        check_ack_recv=skt.recv(7)
        if check_ack_recv.decode()!="<<ACK>>":
            print("error-"+check_ack_recv.decode())
        file.close()
        pendingconfirmation_label["text"]="File Sent"
        popup_file.protocol("WM_DELETE_WINDOW",lambda: destroy(popup_file))
        file_send_event.set()
    return
# File Recieve Function
def file_recieve(initialdata):
    global filename,sending_queue,ack_counter_send,file_directory,file,folder_sending
    first_time=True
    if folder_sending:
        ack_counter_send=0
        size=filename.split("\n")[1]
        size=int(size[1:-7])
        totalsize=size
        while size:
            ack_counter_send=0
            ack_counter_send_checker = 512 << 10
            if initialdata:
                if initialdata.decode()!="<<NODIR>>":
                    try:
                        os.mkdir(os.path.join(file_directory,initialdata.decode()))
                    except FileExistsError:
                        pass
                    temp_file_directory=os.path.join(file_directory,initialdata.decode())
                else:
                    temp_file_directory=file_directory
                initialdata=None
            else:
                select.select([skt.fileno()],[],[])
                data=skt.recv(recieve_size)
                if data.decode()!="<<NODIR>>":
                    try:
                        os.mkdir(os.path.join(file_directory,data.decode()))
                    except FileExistsError:
                        pass
                    temp_file_directory=os.path.join(file_directory,data.decode())
                else:
                    temp_file_directory=file_directory
            if first_time:
                file_send_event.clear()
                sending_queue.put("<<ACK>>".encode())
                first_time=False
            else:
                select.select([],[skt.fileno()],[])
                skt.sendall("<<ACK>>".encode())
            # print("Sent ACK of directory")
            select.select([skt.fileno()],[],[])
            data=skt.recv(recieve_size).decode()
            file=open(temp_file_directory+"/"+data.split('\n')[0],"wb")
            temp_sizeoffile=int(data.split('\n')[1][1:-7])
            select.select([],[skt.fileno()],[])
            skt.sendall("<<ACK>>".encode())
            # print("Sent ACK of filename")
            while temp_sizeoffile:
                select.select([skt.fileno()],[],[])
                data=skt.recv(min(recieve_size,temp_sizeoffile))
                if data:
                    file.write(data)
                    ack_counter_send_checker-=len(data)
                    if ack_counter_send_checker<=0:
                        ack_counter_send+=1
                        ack_counter_send_checker += 512 << 10
                    size-=len(data)
                    temp_sizeoffile-=len(data)
                    file_send_progressbar['value']=int(((totalsize-size)/(totalsize))*100)
                    percentage_label["text"]=str(int(((totalsize-size)/(totalsize))*100))+"%"
                    if ack_counter_send==100:
                        select.select([],[skt.fileno()],[])
                        skt.sendall("<<ACK>>".encode())
                        ack_counter_send=0
            select.select([skt.fileno()],[],[])
            data=skt.recv(recieve_size)
            if data.decode()=="<<EOF>>":
                select.select([],[skt.fileno()],[])
                skt.sendall("<<ACK>>".encode())
                # print("Sent ACK of EOF")
            file.close()
        folder_sending=False
        pendingconfirmation_label["text"]="Folder Recieved"
        popup_file.protocol("WM_DELETE_WINDOW",lambda: destroy(popup_file))
        file_status["text"]="Status: Folder Recieved Succesfully"
        file_send_event.set()
    else:
        ack_counter_send=0
        size=filename.split("\n")[1]
        size=int(size[1:-7])
        totalsize=size
        file.write(initialdata)
        ack_counter_send+=1
        size-=len(initialdata)
        file_send_progressbar['value']=int(((totalsize-size)/(totalsize))*100)
        percentage_label["text"]=str(int(((totalsize-size)/(totalsize))*100))+"%"
        ack_counter_send_checker = 512 << 10
        # sending_queue.put("<<ACK>>".encode())
        while size:
            select.select([skt.fileno()],[],[])
            data=skt.recv(min(recieve_size,size))
            if data:
                file.write(data)
                size-=len(data)
                ack_counter_send_checker-=len(data)
                if ack_counter_send_checker<=0:
                    ack_counter_send+=1
                    ack_counter_send_checker += 512 << 10
                file_send_progressbar['value']=int(((totalsize-size)/(totalsize))*100)
                percentage_label["text"]=str(int(((totalsize-size)/(totalsize))*100))+"%"
                if ack_counter_send==100:
                    if first_time:
                        file_send_event.clear()
                        sending_queue.put("<<ACK>>".encode())
                        first_time=False
                    else:
                        select.select([],[skt.fileno()],[])
                        skt.sendall("<<ACK>>".encode())
                    ack_counter_send=0
        select.select([skt.fileno()],[],[])
        data=skt.recv(recieve_size)
        if data.decode()=="<<EOF>>":
            select.select([],[skt.fileno()],[])
            skt.sendall("<<ACK>>".encode())
        file.close()
        pendingconfirmation_label["text"]="File Recieved"
        popup_file.protocol("WM_DELETE_WINDOW",lambda: destroy(popup_file))
        file_status["text"]="Status: File Recieved Succesfully"
        file_send_event.set()
    return
def rejectfile(dropdown_var):
    global pendingconfirmation_label,popup_file,folder_sending
    if dropdown_var and dropdown_var.get()=="Host(Recieve File)":
        sending_queue.put("<<REJECTFILE>>".encode())
        folder_sending=False
        popup_file.destroy()
        popup_file.update()
    else:
        pendingconfirmation_label["text"]="Host Rejected(You can close this Window)"
        popup_file.protocol("WM_DELETE_WINDOW",lambda : destroy(popup_file))
def acceptfile(acceptfile_butt,rejectfile_butt):
    global file,file_directory,pendingconfirmation_label,filename
    if dropdown_var.get()=="Client(Send File)":
        if folder_sending:
            pendingconfirmation_label["text"]="Sending..."
            file_send()
        else:
            file=open(file_directory,"rb")
            pendingconfirmation_label["text"]="Sending..."
            file_send()
    else:
        pendingconfirmation_label["text"]="Receiving..."
        file_directory=filename_var.get()[10:]
        if folder_sending:
            try:
                os.mkdir(os.path.join(file_directory,filename.split("\n")[0]))
            except FileExistsError:
                pass
            file_directory=os.path.join(file_directory,filename.split("\n")[0])
        else:
            file=open(file_directory+"/"+filename.split("\n")[0],"wb")
        sending_queue.put("<<ACCEPTFILE>>".encode())
        acceptfile_butt["state"]="disabled"
        rejectfile_butt["state"]="disabled"
        # file_recieve_thread=th.Thread(target=file_recieve,args=())
        # file_recieve_thread.start()
# Sender/Reciever Working
def reciever():
    global skt,start_disconnect,reciever_queue,recieve_size,filename,ack_counter_send,folder_sending
    while True:
        try:
            select.select([skt.fileno()],[],[])
            recieve_data=skt.recv(recieve_size)
            if not recieve_data:
                start_disconnect=True
                disconnect()
                return
            try:
                backend_data=recieve_data.decode()
                if backend_data=="<<DISCONNECT>>":
                    disconnect()
                    return
                elif backend_data.split("//")[0]=="<<FILEREQUEST>>":
                    filename=recieve_data.decode().split("//")[1]
                    sendfile()
                elif backend_data.split("//")[0]=="<<FOLDERREQUEST>>":
                    folder_sending=True
                    filename=recieve_data.decode().split("//")[1]
                    sendfile()
                elif backend_data=="<<ACCEPTFILE>>":
                    acceptfile(None,None)
                elif backend_data=="<<REJECTFILE>>":
                    rejectfile(None)
                else:
                    file_recieve(recieve_data)
            except UnicodeDecodeError:
                file_recieve(recieve_data)
        except ValueError:
            # print("ValueError")
            return
        except OSError:
            # print("OSError")
            return
def sender():
    global skt,sending_queue,file_send_event
    while True:
        try:
            select.select([],[skt.fileno()],[])
            if start_disconnect:
                skt.sendall("<<DISCONNECT>>".encode())
                return
            if sending_queue.qsize()!=0:
                skt.sendall(sending_queue.get())
                file_send_event.wait()
        except ValueError:
            # print("ValueError")
            return
        except OSError:
            # print("OSError")
            return
# Working
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ans=s.getsockname()
    s.close()
    return ans
def dropdown_check(value):
    global skt,serverskt
    if value=="Client(Send File)":
        connect_start_var.set("Connect")
        ip1["state"]="normal"
        ip2["state"]="normal"
        ip3["state"]="normal"
        ip4["state"]="normal"
        ip1_var.set('')
        ip2_var.set('')
        ip3_var.set('')
        ip4_var.set('')
        port_var.set('')
        port["state"]="normal"
        filename_var.set("Disconnected")
        ipaddr_text["text"]='Enter IP Address of Host(Values between 0-255)'
        port_text["text"]='Enter Port of Host\n(Value between 1024-49151)'
        file_button["text"]="Select File to Send"
        file_button.grid_forget()
        file_button.grid(row=4,column=0,columnspan=5,pady=2,sticky='e')
        selectfolder_button.grid(row=4,column=5,columnspan=4,pady=2,sticky='w')
        file_status.grid_forget()
        sendfile_button.grid(row=6,column=0,columnspan=9,pady=2)
        skt=socket.socket()
    else:
        connect_start_var.set("Start")
        ip=get_ip_address()[0].split('.')
        ip1["state"]="disabled"
        ip2["state"]="disabled"
        ip3["state"]="disabled"
        ip4["state"]="disabled"
        ip1_var.set(ip[0])
        ip2_var.set(ip[1])
        ip3_var.set(ip[2])
        ip4_var.set(ip[3])
        port_var.set('')
        port["state"]="normal"
        filename_var.set("Not Started")
        ipaddr_text["text"]='IP Address'
        file_button["text"]="Select Download Location"
        file_button.grid_forget()
        file_button.grid(row=4,column=0,columnspan=9,pady=2)
        port_text["text"]='Port\n(Value between 1024-49151)'
        sendfile_button.grid_forget()
        selectfolder_button.grid_forget()
        file_status.grid(row=6,column=0,columnspan=9,pady=2)
        serverskt=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
# Validation
def validateip(value):
    if not value:
            return True
    try:
        if int(value)>=0 and int(value)<=255 and len(value)<=3:
            return True
        else:
            return False
    except ValueError:
        return False
def validateport(value):
    if not value:
            return True
    try:
        if int(value)>=0 and int(value)<=65535 and len(value)<=5:
            return True
        else:
            return False
    except ValueError:
        return False
validateipreg=base.register(validateip)
validateportreg=base.register(validateport)
# Elements
dropdown_var = tk.StringVar(value="Select User")
dropdown_label = tk.Label(base, text="Host")
dropdown=tk.OptionMenu(base,dropdown_var,*["Host(Recieve File)","Client(Send File)"],command=dropdown_check)
ip1_var=tk.StringVar()
ip2_var=tk.StringVar()
ip3_var=tk.StringVar()
ip4_var=tk.StringVar()
port_var=tk.StringVar(value="")
ip1=tk.Entry(base,textvariable=ip1_var,width=9,justify="center",validate="all",validatecommand=(validateipreg,'%P'),state="disabled")
ip2=tk.Entry(base,textvariable=ip2_var,width=9,justify="center",validate="all",validatecommand=(validateipreg,'%P'),state="disabled")
ip3=tk.Entry(base,textvariable=ip3_var,width=9,justify="center",validate="all",validatecommand=(validateipreg,'%P'),state="disabled")
ip4=tk.Entry(base,textvariable=ip4_var,width=9,justify="center",validate="all",validatecommand=(validateipreg,'%P'),state="disabled")
port=tk.Entry(base,textvariable=port_var,width=15,justify="center",validate="all",validatecommand=(validateportreg,'%P'),state="disabled")
fullstop=[tk.Label(base,text='.'),tk.Label(base,text='.'),tk.Label(base,text='.')]
colon=tk.Label(base,text=':')
connect_start_var=tk.StringVar(value="Connect")
connect_start=tk.Button(base,textvariable=connect_start_var,state="disabled")
ipaddr_text=tk.Label(base,text='')
port_text=tk.Label(base,text='')
filename_var=tk.StringVar(value='Select User Type')
filename_text=tk.Label(base,textvariable=filename_var,wraplength=400)
file_button=tk.Button(base,text='',state='disabled')
file_status=tk.Label(base,text='Status: ')
sendfile_button=tk.Button(base,text='Send',state='disabled')
selectfolder_button=tk.Button(base,text='Select Folder to Send',state='disabled')
disconnect_button=tk.Button(base,text='Disconnect',state='disabled')
# Placing Elements
dropdown.grid(row=0,column=0,columnspan=10)
ipaddr_text.grid(row=1,column=0,columnspan=8)
port_text.grid(row=1,column=8)
ip1.grid(row=2,column=0,padx=5)
ip2.grid(row=2,column=2,padx=5)
ip3.grid(row=2,column=4,padx=5)
ip4.grid(row=2,column=6,padx=5)
port.grid(row=2,column=8,padx=5)
fullstop[0].grid(row=2,column=1)
fullstop[1].grid(row=2,column=3)
fullstop[2].grid(row=2,column=5)
colon.grid(row=2,column=7)
connect_start.grid(row=3,column=0,columnspan=9,pady=2)
file_button.grid(row=4,column=0,columnspan=9,pady=2)
filename_text.grid(row=5,column=0,columnspan=9,pady=2)
disconnect_button.grid(row=7,column=0,columnspan=9,pady=2)
# Trace
def check_connectstart(*args):
    ip_check = [ip1_var.get(),ip2_var.get(),ip3_var.get(),ip4_var.get()]
    check=0
    for x in ip_check:
        if x and int(x)>=0 and int(x)<=255:
            check+=1
    if port_var.get() and int(port_var.get())<=65535 and int(port_var.get())>=1024 and check==4:
        connect_start["state"]="normal"
    else:
        connect_start["state"]="disabled"
ip1_var.trace_add("write",callback=check_connectstart)
ip2_var.trace_add("write",callback=check_connectstart)
ip3_var.trace_add("write",callback=check_connectstart)
ip4_var.trace_add("write",callback=check_connectstart)
port_var.trace_add("write",callback=check_connectstart)
# Working
def client_connection(connecting_label,popup):
    global skt,connection_accepted,reciever_thread,sender_thread
    try:
        skt.connect((ip1_var.get()+'.'+ip2_var.get()+'.'+ip3_var.get()+'.'+ip4_var.get(),int(port_var.get())))
        connecting_label["text"]='Connecting...'+"\n(Your Address : "+get_ip_address()[0]+")"
    except ConnectionRefusedError:
        connecting_label["text"]="Connection Refused"
        skt.close()
        skt=socket.socket()
        popup.protocol("WM_DELETE_WINDOW",lambda: destroy(popup))
        return
    except TimeoutError:
        connecting_label["text"]="Connection Timed Out"
        skt.close()
        skt=socket.socket()   
        popup.protocol("WM_DELETE_WINDOW",lambda: destroy(popup))
        return
    except OSError:
        skt.close()
        skt=socket.socket()
        connecting_label["text"]="Incorrect IP/Port"
        popup.protocol("WM_DELETE_WINDOW",lambda: destroy(popup))
        return
    try:
        select.select([skt.fileno()],[],[])
        firstrecv=skt.recv(1024).decode()
        if(firstrecv=='accepted'):
            connection_accepted=True
            connecting_label["text"]="Connection Accepted\n(Close this window)"
            connect_start["state"]="disabled"
            file_button["state"]="normal"
            selectfolder_button["state"]="normal"
            filename_var.set("No File Selected")
            disconnect_button["state"]="normal"
            dropdown["state"]="disabled"
            ip1["state"]="disabled"
            ip2["state"]="disabled"
            ip3["state"]="disabled"
            ip4["state"]="disabled"
            port["state"]="disabled"
            reciever_thread=th.Thread(target=reciever, args=())
            sender_thread=th.Thread(target=sender,args=())
            reciever_thread.start()
            sender_thread.start()
            popup.protocol("WM_DELETE_WINDOW",lambda: destroy(popup))
        else:
            connecting_label["text"]="Connection Refused"
            skt.close()
            skt=socket.socket()
            popup.protocol("WM_DELETE_WINDOW",lambda: destroy(popup))
    except ConnectionRefusedError:
        connecting_label["text"]="Connection Refused"
        skt.close()
        skt=socket.socket()
        popup.protocol("WM_DELETE_WINDOW",lambda: destroy(popup))
        return
    except TimeoutError:
        connecting_label["text"]="Connection Timed Out"
        skt.close()
        skt=socket.socket()
        popup.protocol("WM_DELETE_WINDOW",lambda: destroy(popup))
        return
    
def acceptconn(popup_waitconnection):
    global connection_accepted,skt,sender_thread,reciever_thread,file_directory
    connection_accepted=True
    select.select([],[skt.fileno()],[])
    skt.sendall("accepted".encode())
    popup_waitconnection.destroy()
    popup_waitconnection.update()
    connect_start["state"]="disabled"
    file_button["state"]="normal"
    file_directory=str(os.path.abspath(os.getcwd()))
    filename_var.set("Location: "+file_directory)
    disconnect_button["state"]="normal"
    dropdown["state"]="disabled"
    ip1["state"]="disabled"
    ip2["state"]="disabled"
    ip3["state"]="disabled"
    ip4["state"]="disabled"
    port["state"]="disabled"
    reciever_thread=th.Thread(target=reciever, args=())
    sender_thread=th.Thread(target=sender,args=())
    reciever_thread.start()
    sender_thread.start()
    return

def rejectconn(popup_waitconnection):
    global skt,serverskt
    popup_waitconnection.destroy()
    popup_waitconnection.update()
    try:
        skt.close()
    except AttributeError:
        pass
    serverskt.close()
    serverskt=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    return

def host_connection(pendingconnection_label,acceptconn_butt,rejectconn_butt):
    global serverskt,skt
    try:
        skt, incoming_addr=serverskt.accept()
    except OSError:
        return
    pendingconnection_label["text"]='Accept Connection from'+str(incoming_addr).split(",")[0]+')?'
    acceptconn_butt["state"]="normal"
    rejectconn_butt["state"]="normal"
def connect():
    global port_var,base
    if not(int(port_var.get())>=1024 and int(port_var.get())<=49151):
        popup=tk.Toplevel(base)
        popup.geometry("+%d+%d" %(base.winfo_x(),base.winfo_y()))
        error_port_label=tk.Label(popup,text="Incorrect Port Number")
        error_port_label.pack()
        return
    if connect_start_var.get()=="Connect":
        popup_attemptconnection=tk.Toplevel(base)
        popup_attemptconnection.geometry("+%d+%d" %(base.winfo_x(),base.winfo_y()))
        popup_attemptconnection.minsize(width=300,height=100)
        popup_attemptconnection.columnconfigure(index=0,minsize=100)
        popup_attemptconnection.rowconfigure(index=0,minsize=300)
        connecting_label=tk.Label(popup_attemptconnection,text="",justify='center')
        connecting_label.pack()
        popup_attemptconnection.grab_set()
        client_connection_thread=th.Thread(target=client_connection,args=(connecting_label,popup_attemptconnection,))
        client_connection_thread.start()
        popup_attemptconnection.protocol("WM_DELETE_WINDOW",donothing)
    else:
        popup_waitconnection=tk.Toplevel(base)
        popup_waitconnection.geometry("+%d+%d" %(base.winfo_x(),base.winfo_y()))
        popup_waitconnection.minsize(width=300,height=100)
        popup_waitconnection.columnconfigure(0,minsize=150)
        popup_waitconnection.columnconfigure(1,minsize=150)
        popup_waitconnection.rowconfigure(0,minsize=50)
        popup_waitconnection.rowconfigure(1,minsize=50)
        pendingconnection_label=tk.Label(popup_waitconnection,text='Waiting for Connection',justify="center")
        pendingconnection_label.grid(row=0,column=0,columnspan=2,sticky='nsew')
        acceptconn_butt=tk.Button(popup_waitconnection,justify='center',text='Yes',command=lambda: acceptconn(popup_waitconnection),state='disabled')
        acceptconn_butt.grid(row=1,column=0,sticky='nsew',padx=10)
        rejectconn_butt=tk.Button(popup_waitconnection,justify='center',text='No',command=lambda: rejectconn(popup_waitconnection),state='disabled')
        rejectconn_butt.grid(row=1,column=1,sticky='nsew',padx=10)
        popup_waitconnection.protocol("WM_DELETE_WINDOW",lambda: rejectconn(popup_waitconnection))
        serverskt.bind((ip1_var.get()+'.'+ip2_var.get()+'.'+ip3_var.get()+'.'+ip4_var.get(),int(port_var.get())))
        serverskt.listen(1)
        popup_waitconnection.grab_set()
        server_connection_thread=th.Thread(target=host_connection,args=(pendingconnection_label,acceptconn_butt,rejectconn_butt))
        server_connection_thread.start()
connect_start["command"]=connect
def getfile():
    global sendfile_button,filename_var,file_directory,folder_sending
    if file_button["text"]=="Select File to Send":
        temp_file_directory=askopenfilename()
        if temp_file_directory:
            sendfile_button["state"]="normal"
            filename_var.set(temp_file_directory.split("/")[-1]+'\n('+str(os.path.getsize(temp_file_directory))+' Bytes)')
            file_directory=temp_file_directory
            folder_sending=False
    else:
        download_location=filedialog.askdirectory()
        if download_location:
            filename_var.set("Location: "+download_location)
            file_directory=download_location
file_button["command"]=getfile
def getfolder():
    global sendfile_button,filename_var,file_directory,folder_sending
    temp_file_directory=filedialog.askdirectory()
    if temp_file_directory:
        sendfile_button["state"]="disabled"
        file_directory=temp_file_directory
        temp_size=0
        for path, dirs, files in os.walk(file_directory):
            for f in files:
                fp = os.path.join(path, f)
                temp_size += os.path.getsize(fp)
        filename_var.set(temp_file_directory.split("/")[-1]+'\n('+str(temp_size)+' Bytes)')
        sendfile_button["state"]="normal"
        folder_sending=True
selectfolder_button["command"]=getfolder
def sendfile():
    global sendfile_button,base,dropdown_var,popup_file,pendingconfirmation_label,filename_var,file_send_progressbar,filename
    global percentage_label
    popup_file=tk.Toplevel(base)
    popup_file.geometry("+%d+%d" %(base.winfo_x(),base.winfo_y()))
    popup_file.grab_set()
    if dropdown_var.get()=="Client(Send File)":
        popup_file.minsize(width=300,height=100)
        if folder_sending:
            sending_queue.put(("<<FOLDERREQUEST>>//"+filename_var.get()).encode())
        else:
            sending_queue.put(("<<FILEREQUEST>>//"+filename_var.get()).encode())
    else:
        popup_file.minsize(width=300,height=133)
    popup_file.columnconfigure(0,minsize=150)
    popup_file.columnconfigure(1,minsize=150)
    popup_file.rowconfigure(0,minsize=33)
    popup_file.rowconfigure(1,minsize=33)
    popup_file.rowconfigure(2,minsize=33)
    pendingconfirmation_label=tk.Label(popup_file,text='Waiting for host to accept.',justify="center",wraplength=300)
    pendingconfirmation_label.grid(row=0,column=0,columnspan=2,sticky='nsew')
    if dropdown_var.get()=="Host(Recieve File)":
        popup_file.rowconfigure(3,minsize=33)
        if folder_sending:
            pendingconfirmation_label["text"]="Accept Folder(It will be created for you):\n  "+filename+"?"
        else:
            pendingconfirmation_label["text"]="Accept File:  "+filename+"?"
    file_send_progressbar=ttk.Progressbar(popup_file, orient="horizontal",length=250,mode="determinate")
    file_send_progressbar.grid(row=1,column=0,columnspan=2)
    percentage_label=tk.Label(popup_file,text='0%',justify="center")
    percentage_label.grid(row=2,column=0,columnspan=2)
    if dropdown_var.get()=="Host(Recieve File)":
        rejectfile_butt=tk.Button(popup_file,justify='center',text='Reject',command=lambda: rejectfile(dropdown_var))
        rejectfile_butt.grid(row=3,column=1,sticky='nsew',padx=10)
        acceptfile_butt=tk.Button(popup_file,justify='center',text='Accept',command=lambda: acceptfile(acceptfile_butt,rejectfile_butt))
        acceptfile_butt.grid(row=3,column=0,sticky='nsew',padx=10)
        if shutil.disk_usage(file_directory)[2]<int(filename.split('\n')[1][1:-7]):
            acceptfile_butt["state"]="disabled"
            if folder_sending:
                pendingconfirmation_label["text"]="Accept Folder(It will be created for you):  "+filename+"?"+"(Not Enough Space in current directory)"
            else:
                pendingconfirmation_label["text"]="Accept:  "+filename+"?"+"(Not Enough Space in current directory)"
    popup_file.protocol("WM_DELETE_WINDOW",donothing)
    return
sendfile_button["command"]=sendfile
def disconnect():
    global serverskt,skt,start_disconnect
    connect_start["state"]="normal"
    disconnect_button["state"]="disabled"
    file_button["state"]="disabled"
    selectfolder_button["state"]="disabled"
    sendfile_button["state"]="disabled"
    dropdown["state"]="normal"
    filename_var.set("Disconnected")
    if dropdown_var.get()=='Client(Send File)':
        ip1["state"]="normal"
        ip2["state"]="normal"
        ip3["state"]="normal"
        ip4["state"]="normal"
        skt.close()
        skt=socket.socket()
    else:
        if not start_disconnect:
            start_disconnect=True
        else:
            start_disconnect=False
            skt.close()
            skt=socket.socket()
            serverskt.close()
            serverskt=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    port["state"]="normal"
disconnect_button["command"]=disconnect
def endprogram():
    global base
    base.destroy()
    if skt:
        skt.close()
    if serverskt:
        serverskt.close()
    os._exit(1)
base.protocol("WM_DELETE_WINDOW",endprogram)
base.mainloop()