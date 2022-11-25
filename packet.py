class Packet():				# the class for packet and its header values

	def __init__(self, sNum, data, FIN=False):
		self.seqnum = sNum					# the sequence number of the packet
		self.data = data					# the data contained
		self.FIN = FIN						# the boolean value to indicate the final packet

