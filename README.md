# RDT_over_UDP

Our UDP-FTP offers reliable data transfer(RDT) features by implementing some of the basic and important principles of RDT at the application level (i.e FTP) and using UDP as transport layer protocol.

The features offered by our application as part of RDT are:
* Packet acknowledgment 
    * Cumulative ACKS
* Packet loss detection 
    * Timeout
    * Duplicate ACKS
* Packet retransmission
    * Fast Retransmit
* Pipelined RDT
* Synchronous jobs at the sender
* Delayed ACKS
* Dynamic Timeout and Round-Trip Time Estimation
* Congestion Control
* Connection Management
