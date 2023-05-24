#new receiver_mod#  
import json
import socket
import time
import matplotlib.pyplot as plt
import random
from socket import timeout

def load_parameters(json_file='../Params.json'):
    """
    Load parameters from a JSON file.

    :param json_file: Path to the JSON file containing parameters
    :return: Dictionary containing parameters
    """
    with open(json_file) as params:
        data = json.load(params)
    return data

def print_transfer_info(start_time, end_time, elapsed_time, packets_count, bytes_count):
    """
    Print file transfer information.

    :param start_time: Start time of file receiving
    :param end_time: End time of file receiving
    :param elapsed_time: Elapsed time of file receiving
    :param packets_count: Number of packets received
    :param bytes_count: Number of bytes received
    """
    transfer_info = f"""
    Start time of file receiving: {time.strftime("%H:%M:%S", time.localtime(start_time))}
    End time of file receiving: {time.strftime("%H:%M:%S", time.localtime(end_time))}
    Elapsed time of file receiving: {round(elapsed_time, 2)} s
    No of packets: {packets_count}
    No of bytes: {round(bytes_count / 1000000, 3)} MB
    """
    print(transfer_info)

def receiver(server_ip, server_port, plot_loss=True, params=None):
    """
    Receive files using UDP.

    :param server_ip: Server IP address
    :param server_port: Server port
    :param plot_loss: Whether to plot packet ID vs time (default is True)
    :param params: Dictionary containing parameters (default is None)
    """
    if params is None:
        params = load_parameters()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))
    server_socket.settimeout(params['TIMEOUT'])
    print("The server is ready to receive")

    expected_packet_id = 0
    good_packets = []
    sent_packets = []
    retransmitted_packets = []
    dropped_packets = 0
    transfer_start_time = time.time()

    while True:
        try:
            message, clientAddress = server_socket.recvfrom(2048)

            packet_id = int.from_bytes(message[:2], "big")
            file_id = int.from_bytes(message[2:4], "big")
            application_data = message[4:]
            print((packet_id, file_id, 'data'))
            if packet_id == expected_packet_id:
                rnd = random.randint(0, 100)
                if rnd > params['DROP_PROB']:
                    ACK = message[:2] + message[2:4]
                    server_socket.sendto(ACK, clientAddress)
                    good_packets.append(message)
                    expected_packet_id += 1

                    sent_packets.append((packet_id, time.time()))
                else:
                    print(f'Packet {packet_id} Dropped')
                    dropped_packets += 1
            elif packet_id > expected_packet_id:
                if expected_packet_id > 0:
                    ACK = (expected_packet_id - 1).to_bytes(2, "big") + message[2:4]
                    server_socket.sendto(ACK, clientAddress)

                retransmitted_packets.append((packet_id, time.time()))

            if good_packets and int.from_bytes(good_packets[-1][-2:], "big") == 0xFFFF:
                break
        except socket.timeout:
            print("Receiver timeout occurred. Exiting the loop.")
            continue

    transfer_end_time = time.time()
    elapsed_time = transfer_end_time - transfer_start_time
    packets_count = len(good_packets)
    bytes_count = sum([len(packet[4:-2]) for packet in good_packets])
    print_transfer_info(transfer_start_time, transfer_end_time, elapsed_time, packets_count, bytes_count)

    # Save received data to a file
    with open("received_file.png", "wb") as f:
        f.write(b''.join([packet[4:-2] for packet in good_packets]))

    # Calculate the actual loss rate and retransmitted packets
    total_packets = len(good_packets) + len(retransmitted_packets)
    if total_packets == 0:
        actual_loss_rate = 0
    else:
        actual_loss_rate = round((len(retransmitted_packets) / total_packets) * 100, 2)

    print(f"Actual loss rate: {actual_loss_rate}%")

    # Plot packet ID vs time
    if plot_loss:
        if sent_packets:
            sent_packet_ids, sent_timestamps = zip(*sent_packets)
            plt.scatter(sent_timestamps, sent_packet_ids, c="pink", marker="s", edgecolor="green", linewidths=1, s=10)
        if retransmitted_packets:
            retransmitted_packet_ids, retransmitted_timestamps = zip(*retransmitted_packets)
            plt.scatter(retransmitted_timestamps, retransmitted_packet_ids, c="yellow", edgecolor="red", linewidths=1, s=10)

        plt.legend(["sent", "retransmitted"], loc="lower right")
        plt.xlabel("Time")
        plt.ylabel("Packet ID")
        plt.title(f"Window Size: {params['WINDOW_SIZE']} packets, Timeout Interval: {params['TIMEOUT']} ms \nRetransmitted packets: {len(retransmitted_packets)}, actual loss rate: {actual_loss_rate}%")
        plt.show()


if __name__ == '__main__':
    params = load_parameters()
    kwargs = {'server_ip': params["SERVER"], 'server_port': params["receiver_port"]}
    while True:
        receiver(**kwargs)
        receive_another_file = input("Do you want to receive another file? (yes/no)(y/n): ")
        if receive_another_file.lower() not in ["yes", "y"]:
            break