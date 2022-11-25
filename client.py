import socket
import sys
import os
import pickle								# header files imported
import time
from packet import *
import threading

PORT = 9999	
SERVER_IP = '192.168.117.74'	# IP address of server to be configured
BUF_SIZE = 65536
FILE_BUF = 60000						
ADDR = (SERVER_IP, PORT)

TIMEOUT = 0.1 						# the timeout for a socket
START_RTT_TIME = -1					# the start time of round trip time
ESTIMATED_RTT = TIMEOUT				# the estimated round trip time
DEV_RTT = 0							# the deviated round trip time
DEV_DEV_RTT = 0						# the deviation of deviated round trip time
GAMMA = 0.5							# the hyperparameter for DEV_DEV_RTT

EXP_SNUM = 0						# the expected sequence number
NEXT_SNUM = 0						# the next sequence number of the packet to be sent

WINDOW = 1							# intial window size
MAX_WINDOW = 16						# the maximum window size
WINDOW_LIST = []					# the list of messages that have been sent but not acknowledged
ALPHA = 2							# window factor
BETA = 0.1							# step size



def update_timeout(sample_rtt):					# the function for updating the timeout as per our algorithm

	global ESTIMATED_RTT
	global DEV_RTT
	global DEV_DEV_RTT							# the global variables
	global GAMMA
	
	ESTIMATED_RTT = 0.875*ESTIMATED_RTT + 0.125*sample_rtt
	DEV_RTT = 0.75*DEV_RTT + 0.25*abs(sample_rtt - ESTIMATED_RTT)
	DEV_DEV_RTT = (1-GAMMA)*DEV_DEV_RTT + GAMMA*abs( abs(sample_rtt - ESTIMATED_RTT) - DEV_RTT)					# our derived formula
	
	TIMEOUT = ESTIMATED_RTT + 4*DEV_RTT + (24*GAMMA -2)*DEV_DEV_RTT


def rdt_pipeline_send(msg):						# the function for sending the message in a pipelined fashion

	global EXP_SNUM
	global NEXT_SNUM
	global WINDOW								# global variables
	global ADDR
	global WINDOW_LIST
	global START_RTT_TIME

	NEXT_SNUM += 1
	WINDOW_LIST.append(msg)						# the message is sent and appended to the window list
	client.sendto(msg,ADDR)

	if START_RTT_TIME ==-1:						# the start time of round trip time is recorded
		START_RTT_TIME = time.time()

	while NEXT_SNUM - EXP_SNUM >= WINDOW:
		pass									# while the window is filled

	return True


def rdt_check():								# the function to check the reliability in data transfer

	global EXP_SNUM
	global ADDR
	global WINDOW
	global WINDOW_LIST							# the global variables
	global TIMEOUT
	global START_RTT_TIME
	global ALPHA
	global BETA
	
	last_last_ack = None
	last_ack = None								# the last and last-to-last acknowledged packets' seqnums
	
	timeouts = 0	

	while timeouts<10:

		isack = False

		if len(WINDOW_LIST) !=0:
			client.settimeout(TIMEOUT)				# if the window list is not empty add a timeout 
		else:
			client.settimeout(None)
		
		while not isack and timeouts<10:							# until the acknowledgement is not received for a specific packet 

			try:
				chunk = client.recvfrom(BUF_SIZE)		# the chunk is received
				timeouts = 0
				client.settimeout(TIMEOUT)
				rcvpkt = pickle.loads(chunk[0])
				
				if last_last_ack and last_ack and last_last_ack == last_ack and last_ack == rcvpkt.seqnum and len(WINDOW_LIST) !=0:
					msg = WINDOW_LIST[0]
					client.sendto(msg,ADDR)						# the fast retransmission

				isack = (rcvpkt.seqnum >= EXP_SNUM)				# if the acknowledgement is given for more than the sequence number expected then it is true
				last_last_ack = last_ack
				last_ack = rcvpkt.seqnum				

				if isack:
					if START_RTT_TIME != -1:
						sample_rtt = time.time() - START_RTT_TIME
						START_RTT_TIME = -1								# the round trip time is calculated and then used to get optimal TIMEOUT
						update_timeout(sample_rtt)
					
					WINDOW = min( WINDOW * ALPHA, MAX_WINDOW)			# the window is updated as per our algorithm
			
			except socket.timeout:
				timeouts += 1	
				if len(WINDOW_LIST)!=0:
					msg = WINDOW_LIST[0]									# the top element in WINDOW LIST is the required packet to be retransmitted
					client.sendto(msg,ADDR)
					WINDOW /= ALPHA
					ALPHA = max(1, ALPHA - BETA)							# updated as per our algorithm


		dif = EXP_SNUM
		EXP_SNUM = rcvpkt.seqnum+1										
		dif = EXP_SNUM - dif

		WINDOW_LIST = WINDOW_LIST[dif:]									# the packets are removed from WINDOW LIST accordingly

		if rcvpkt.FIN:
			break


filename = sys.argv[1]							# the file name
file = open(filename, "rb")
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)				# the UDP socket connection

pkt = Packet(0, str.encode(filename))
msg = pickle.dumps(pkt)

thread = threading.Thread(target=rdt_check, daemon=True)				# a separate thread that takes care of acknowledgements
thread.start()

start = time.time()
rdt_pipeline_send(msg)					# function call for pipeline sending

num_packets = 0
byte_count = 0

data = file.read(FILE_BUF)
pkt = Packet(num_packets+1, data)
msg = pickle.dumps(pkt)

while data:
	if rdt_pipeline_send(msg):						# only after the function returns we can send the next packet
		num_packets += 1
		byte_count += len(data)
		data = file.read(FILE_BUF)
		pkt = Packet(num_packets+1, data)
		msg = pickle.dumps(pkt)		


pkt = Packet(num_packets+1, None, FIN=True)
msg = pickle.dumps(pkt)
rdt_pipeline_send(msg)

thread.join()										# the thread is joined to main thread

end = time.time()	
file.close()
client.close()										# socket and file close

print("Number of packets sent:", num_packets)
print("Actual size of file:", os.path.getsize(filename))					# the necessary information is printed
print("Byte count of file:", byte_count)
print("Total time to transfer file:", end - start)


