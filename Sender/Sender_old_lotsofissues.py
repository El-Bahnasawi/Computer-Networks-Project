#old sender#
from socket import *
import math
import random
import time
import json

f = open('../Params.json')
data = json.load(f)

def sender(filename: str, receiver_IP_address: str, receiver_port: int):
    def prepare_packets(filename: str) -> tuple:
        MSS = 1024
        file_id = random.randint(0, 65536)
        with open(filename, "rb") as image:
            f = image.read()
            data = bytearray(f)
        num_packets = math.ceil(len(data) / MSS)
        
        while num_packets > 65536:
            MSS = int(input("Enter a larger MSS value: "))
            num_packets = math.ceil(len(data) / MSS)
            print(f"Number of packets is:  {num_packets}")
        
        segments = []
        packet_id = 0
        trailer_id = 0x0000
        while len(data) > 0:
            application_data = data[:MSS]
            data = data[MSS:]
            if len(data) == 0:
                trailer_id = 0xFFFF
            segment = packet_id.to_bytes(2, 'big') + file_id.to_bytes(2, 'big') + application_data + trailer_id.to_bytes(2, 'big')
            segments.append(segment)
            packet_id += 1
        
        return segments  
    
    packets = prepare_packets(filename)

    WINDOW_SIZE = data['WINDOW_SIZE']
    TIMEOUT = data['TIMEOUT']
    DROP_PROB = data['DROP_PROB']
    PACKETS_COUNT = len(packets)

    f.close()

    clientSocket = socket(AF_INET, SOCK_DGRAM)
    clientSocket.settimeout(TIMEOUT)

    base = 0
    next_seq_num = 0
    excepted_ack_id = 0
    retransmissions = 0 

    transfer_start_time = round(time.time(), 3)

    while base < PACKETS_COUNT:
        try:
            while next_seq_num < min(base + WINDOW_SIZE, PACKETS_COUNT):
                rnd = random.randint(0, 100)
    
                if (rnd > DROP_PROB):
                    print('send', next_seq_num)
                    clientSocket.sendto(packets[next_seq_num], (receiver_IP_address, receiver_port))
                    next_seq_num += 1
                else :
                    print(f'Packet {next_seq_num} Dropped')
                    next_seq_num += 1

            ACK, _ = clientSocket.recvfrom(2048)

            ACK_ID = int.from_bytes(ACK[:2], 'big')

            if ACK_ID == excepted_ack_id:
                excepted_ack_id += 1
                base += 1
                print('ACK_ID', ACK_ID)
            elif ACK_ID < excepted_ack_id:
                retransmissions += 1

        except timeout:
            print("Request time out")
            next_seq_num = excepted_ack_id

    end_time = round(time.time(), 3)
    elasped_time = end_time - transfer_start_time
    no_bytes = len(b''.join([packet[4:-2] for packet in packets]))
    average_transfer_rate_packets_sec = round(PACKETS_COUNT / elasped_time, 2)
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
    print(f'No of packets: {PACKETS_COUNT}')
    print(f'No of bytes: {round(no_bytes / 1000000, 3)} MB')
    print(f'Average transfer rate in packets/sec: {average_transfer_rate_packets_sec}')
    print(f'Average transfer rate in bytes/sec: {average_transfer_rate_bytes_sec}')
    print(f"No of retransmissions: {retransmissions} packets")

if __name__ == '__main__':
    kwargs = {'filename': "SmallFile.png", 'receiver_IP_address': data["SERVER"], 'receiver_port': data["receiver_port"]}
    sender(**kwargs)
