from socket import *
import matplotlib.pyplot as plt
import time
import json

f = open('../Params.json')
data = json.load(f)

serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind((data["SERVER"], data["receiver_port"]))
print("The server is ready to receive")

excepted_pkt_id = 0
good_packets = []

# sent packets
x1, y1 = [], []

# retransmitted packets
x2, y2 = [], []

retransmitted_packets = 0
transfer_start_time = round(time.time(), 3)
while True:
    message, clientAddress = serverSocket.recvfrom(2048)

    packet_id = int.from_bytes(message[:2], "big")
    file_id = int.from_bytes(message[2:4], "big")
    trailer_id = int.from_bytes(message[-2:], "big")
    print((packet_id, file_id, 'data', trailer_id))

    if packet_id == excepted_pkt_id:
        ACK = message[:2] + message[2:4]
        serverSocket.sendto(ACK, clientAddress)
        good_packets.append(message)
        excepted_pkt_id += 1

        y1.append(packet_id)
        x1.append(time.time())
    elif packet_id > excepted_pkt_id:
        ACK = (excepted_pkt_id - 1).to_bytes(2, "big") + message[2:4]
        serverSocket.sendto(ACK, clientAddress)
        
        y2.append(packet_id)
        x2.append(time.time())
        retransmitted_packets += 1
    
    if int.from_bytes(good_packets[-1][-2:], "big") == 0xFFFF:
        break

end_time = round(time.time(), 3)
elasped_time = end_time - transfer_start_time
no_bytes = len(b''.join([packet[4:-2] for packet in good_packets]))
average_transfer_rate_packets_sec = round(len(good_packets) / elasped_time, 2)
average_transfer_rate_bytes_sec = round(no_bytes / elasped_time, 2)

def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    
    return "%d:%02d:%02d" % (hour, minutes, seconds)

print("\n")
print(f'Start time of file transfering: {convert(transfer_start_time)}')
print(f'End time of file transfering: {convert(end_time)}')
print(f'Elasped time of file transfering: {round(elasped_time, 2)} s')
print(f'No of packets: {len(good_packets)}')
print(f'No of bytes: {round(no_bytes / 1000000, 3)} MB')
print(f'Average transfer rate in packets/sec: {average_transfer_rate_packets_sec}')
print(f'Average transfer rate in bytes/sec: {average_transfer_rate_bytes_sec}')
print(f"No of retransmissions: {retransmitted_packets} packets")


binary_data = b''.join([packet[4:-2] for packet in good_packets])
f = open("received_img.png", "wb")
f.write(binary_data)
f.close()

temp = min(x1[0], x2[0])
kwargs = {'linewidths': 1, 's': 10}
plt.scatter(x = [x - temp for x in x1], y = y1, c ="pink", marker ="s", edgecolor ="green", **kwargs)
plt.scatter(x = [x - temp for x in x2], y = y2, c ="yellow", edgecolor ="red", **kwargs)


plt.legend(["sent" , "retransmitted"], loc = "lower right")
plt.title(f"Window Size: {data['WINDOW_SIZE']} packtets, Timeout Interval: {data['TIMEOUT']} ms \nRetransmitted packets: {retransmitted_packets}, loss rate: {round((retransmitted_packets/len(good_packets)) * 100, 2)}%")
plt.xlabel("Time (s)")
plt.ylabel("Packet_ID")
plt.show()

f.close()
serverSocket.close()
