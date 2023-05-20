#sender code#
from socket import *
import math
import random
import time
import json

def print_transfer_info(start_time, end_time, elapsed_time, packets_count, bytes_count, retransmissions, avg_rate_packets_sec, avg_rate_bytes_sec):
    """
    Prints and logs the transfer information of a file transfer.
    
    :param start_time: The start time of the file transfer, in seconds since the epoch
    :param end_time: The end time of the file transfer, in seconds since the epoch
    :param elapsed_time: The total time taken for the file transfer, in seconds
    :param packets_count: The total number of packets sent during the file transfer
    :param bytes_count: The total number of bytes sent during the file transfer
    :param retransmissions: The total number of packets retransmitted during the file transfer
    :param avg_rate_packets_sec: The average transfer rate in packets per second
    :param avg_rate_bytes_sec: The average transfer rate in bytes per second
    """
    def convert(seconds):
        """
        Takes in a number of seconds and converts it into a string representation of time in the format "hh:mm:ss".
        :param seconds: An integer representing the number of seconds to be converted.
        :return: A string representation of time in the format "hh:mm:ss".
        """
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return "%d:%02d:%02d" % (hour, minutes, seconds)
    
    transfer_info = f"""
    Start time of file transferring: {convert(start_time)}
    End time of file transferring: {convert(end_time)}
    Elapsed time of file transferring: {round(elapsed_time, 2)} s
    No of packets: {packets_count}
    No of bytes: {round(bytes_count / 1000000, 3)} MB
    No of retransmissions: {retransmissions}
    Average transfer rate in packets/sec: {avg_rate_packets_sec}
    Average transfer rate in bytes/sec: {avg_rate_bytes_sec}
    """
    print(transfer_info)
    with open("transfer_log.txt", "a") as log_file:
        log_file.write(transfer_info)

# Load parameters from the JSON file
with open('../Params.json') as params:
    data = json.load(params)
    WINDOW_SIZE = data['WINDOW_SIZE']
    TIMEOUT = data['TIMEOUT']
    DROP_PROB = data['DROP_PROB']
if DROP_PROB == 0:
    loss_percentage = float(input("Enter the desired simulation packet loss percentage \n (You can set Default value in Params.json) (between 0% to 20%): "))
    DROP_PROB = 100 - loss_percentage  # Update DROP_PROB accordingly

def sender(filename: str, receiver_IP_address: str, receiver_port: int):
    """
    This function sends a file to a receiver using a specified IP address and port.
    
    :param filename: The name of the file to be sent
    :param receiver_IP_address: The IP address of the receiver
    :param receiver_port: The port number to be used for communication
    """
    def prepare_packets(filename: str) -> tuple:
        """
        This function prepares the packets to be sent.
        
        :param filename: The name of the file to be sent
        :return: A tuple containing the prepared packets
        """
        MSS = 1024
        file_id = random.randint(0, 65536)
        with open(filename, "rb") as image:
            f = image.read()
            data = bytearray(f)
        num_packets = math.ceil(len(data) / MSS)
        
        # Check if the number of packets is larger than the maximum allowed (65536)
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


    PACKETS_COUNT = len(packets)

    clientSocket = socket(AF_INET, SOCK_DGRAM)
    clientSocket.settimeout(TIMEOUT)

    base = 0
    next_seq_num = 0
    excepted_ack_id = 0
    retransmissions = 0 

    transfer_start_time = round(time.time(), 3)

    # Add new variables for congestion control
    ssthresh = float('inf')
    cwnd = 1
    dup_ack_count = 0
    # Initialize variables for SRTT calculation
    estimated_rtt = 0.0
    dev_rtt = 0.0
    alpha = 0.125
    beta = 0.25
    timeout_interval = TIMEOUT
    # ... (previous code omitted for brevity)
    while base < PACKETS_COUNT:
        try:
            while next_seq_num < min(base + int(cwnd), PACKETS_COUNT):
                rnd = random.randint(0, 100)

                if (rnd > DROP_PROB):
                    print('send', next_seq_num)
                    clientSocket.sendto(packets[next_seq_num], (receiver_IP_address, receiver_port))
                    next_seq_num += 1
                else :
                    print(f'Packet {next_seq_num} Dropped')
                    next_seq_num += 1
            send_time = time.time()
            ACK, _ = clientSocket.recvfrom(2048)
            # Calculate RTT and update timeout_interval
            sample_rtt = time.time() - send_time
            estimated_rtt = (1 - alpha) * estimated_rtt + alpha * sample_rtt
            dev_rtt = (1 - beta) * dev_rtt + beta * abs(sample_rtt - estimated_rtt)
            timeout_interval = estimated_rtt + 4 * dev_rtt
            clientSocket.settimeout(timeout_interval)
            ACK_ID = int.from_bytes(ACK[:2], 'big')
            is_dup_ack = ACK[2]

            # Update congestion control
            if ACK_ID == excepted_ack_id:
                if cwnd < ssthresh:
                    cwnd *= 2  # slow start
                else:
                    cwnd += 1  # congestion avoidance

                excepted_ack_id += 1
                base += 1
                print('ACK_ID', ACK_ID)
            elif ACK_ID < excepted_ack_id:
                if is_dup_ack:
                    dup_ack_count += 1
                    if dup_ack_count == 3:
                        ssthresh = cwnd / 2  # fast retransmit
                        cwnd = ssthresh + 3  # fast recovery
                else:
                    dup_ack_count = 0
                    retransmissions += 1

        except timeout:
            print("Request time out")
            next_seq_num = excepted_ack_id
            ssthresh = cwnd / 2
            cwnd = 1
            # Update timeout interval in case of timeout
            timeout_interval *= 2
            clientSocket.settimeout(timeout_interval)
            
            
    end_time = round(time.time(), 3)
    elapsed_time = end_time - transfer_start_time
    no_bytes = len(b''.join([packet[4:-2] for packet in packets]))
    average_transfer_rate_packets_sec = round(PACKETS_COUNT / elapsed_time, 2)
    average_transfer_rate_bytes_sec = round(no_bytes / elapsed_time, 2)
    print_transfer_info(transfer_start_time, end_time, elapsed_time, PACKETS_COUNT, no_bytes, retransmissions, average_transfer_rate_packets_sec, average_transfer_rate_bytes_sec)
    # End of file transmission
    # Ask the user if they want to send another file or not
    send_another_file = input("Do you want to send another file? (yes/no)(y/n): ")
    if send_another_file.lower() == "yes" or send_another_file.lower() == "y":
        # Call the sender function with the new file information
        new_filename = input("Enter the new file name: ")
        sender(new_filename, receiver_IP_address, receiver_port)
if __name__ == '__main__':
    while True:
        kwargs = {'filename': input("Enter the file name: "), 'receiver_IP_address': data["SERVER"], 'receiver_port': data["receiver_port"]}
        sender(**kwargs)
        send_another_file = input("Do you want to send another file? (yes/no)(y/n): ")
        if send_another_file.lower() not in ["yes", "y"]:
            break