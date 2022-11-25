from asyncore import write
import socket
import pickle
from packet import *
import time

PORT = 9999				# server port through which "UDP-FTP" connections are allowed
SERVER_IP = '192.168.117.74' # ip address of server to be configured
CLIENT_IP = None
ADDR = (SERVER_IP, PORT)    # maximum size of the udp datagram recieved
BUF_SIZE = 65536            # the sequence number of the packet currently expected to be acknowledged
EXP_SNUM = 0
TIMEOUT = 5
DELAY = 0.005               # delay by which server performs 'delayed-ACKS'
RCV_SIZE = 16               # recieve buffer size (in packets) of the reciever
RCV_BUFFER = []             # recieve buffer of the reciever


def rotate(l,n):
    return l[n:] + l[:n]

# This function handles sending ACKS (with supposed delays)
# and buffering the out-of-order segments

def rdt_rcv():

    global CLIENT_IP
    global EXP_SNUM
    global RCV_SIZE
    global RCV_BUFFER

    rcv_data = []	# stores the recieved packets within this delay
    
    start_time = -1
    fin = None

    try:
        while True:
            
            chunk = server.recvfrom(BUF_SIZE)
            msg = pickle.loads(chunk[0])

            if not CLIENT_IP:
                # get the IP address from the first packet
                CLIENT_IP = chunk[1]
            
            snum = msg.seqnum

            # '''
			# If the recieved packet has the expected sequence number then
			# we send all the recived packets until this point to the process
            # '''
            if snum == EXP_SNUM:
                RCV_BUFFER[snum-EXP_SNUM] = msg
                
                while (EXP_SNUM -snum < RCV_SIZE and RCV_BUFFER[EXP_SNUM-snum] != None):
                    buf_msg = RCV_BUFFER[EXP_SNUM-snum]
                    rcv_data.append(buf_msg.data)
                    RCV_BUFFER[EXP_SNUM-snum] = None
                    fin = buf_msg.FIN
                    EXP_SNUM+=1
                
                RCV_BUFFER = rotate(RCV_BUFFER,len(rcv_data))
                if start_time == -1:
                    start_time = time.time()
                server.settimeout(DELAY)

			# '''
			# If the recieved packet has a sequence number less than the expected then
			# the server sends an ACK to the last acknowledged packet (duplicate ACK)
			# '''
            elif snum < EXP_SNUM:
                pkt = Packet(EXP_SNUM-1, 0)
                reply = pickle.dumps(pkt)
                server.sendto(reply, CLIENT_IP)

            # '''
			# If the recieved packet has a sequence number greater than the expected then
			# the server stores the packet in the buffer and sends an ACK to
			# the last acknowledged packet (duplicate ACK) like before.
			# '''
            elif snum - EXP_SNUM < RCV_SIZE:
                RCV_BUFFER[snum-EXP_SNUM] = msg
                pkt = Packet(EXP_SNUM-1, 0)
                reply = pickle.dumps(pkt)
                server.sendto(reply, CLIENT_IP)
            
            # '''
			# checking whether the delay is timed out.
			# '''
            if start_time != -1:
                end_time = time.time()
                if end_time - start_time > DELAY:
                    break
                
    except socket.timeout:
        pass

    pkt = Packet(EXP_SNUM-1, 0)		# sending ACK for the last recieved packet.

    if fin:		# if the packet is final, then an ACK with FIN turned on is sent.
        rcv_data = rcv_data[:-1]
        pkt.FIN=True
    
    reply = pickle.dumps(pkt)
    server.sendto(reply, CLIENT_IP)
    server.settimeout(None)
    
    return rcv_data, fin


server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(ADDR)

print("UDP server is up and running...")

def write_to_file(file, rcv_data):
    
    byte_count = 0
    for d in rcv_data:
     if d != None:
         file.write(d)
         byte_count += len(d)
    
    return byte_count

def start():

    global CLIENT_IP
    global EXP_SNUM
    global TIMEOUT
    global RCV_BUFFER
    global RCV_SIZE
    
    while True:
        
        RCV_BUFFER = [None]*RCV_SIZE
        CLIENT_IP = None
        EXP_SNUM = 0

        rcv_data, fin = rdt_rcv()  # calling the reciever for the first time
        # first packet is the filename.
        filename = "rcv_" + rcv_data[0].decode().strip()
        file = open(filename, "wb")

        print("Client", CLIENT_IP, "is sending a file and it is being saved as", filename)

        num_packets = 0
        byte_count = 0

        num_packets += len(rcv_data)-1
        byte_count += write_to_file(file, rcv_data[1:])
        
        while not fin:	 # recieving packet until the FIN packet.
            rcv_data, fin = rdt_rcv()
            num_packets += len(rcv_data)
            byte_count += write_to_file(file, rcv_data)
            
        file.close()
            
        print("File has been received")
        print("Number of packets sent:", num_packets)
        print("Byte count of file:", byte_count)

start()
