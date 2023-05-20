import json
import socket
import time
import matplotlib.pyplot as plt
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
    received_packets = []
    packets_timestamps = []

    transfer_start_time = time.time()

    while True:
        try:
            packet, _ = server_socket.recvfrom(2048)
            packet_id = int.from_bytes(packet[:2], 'big')
            file_id = int.from_bytes(packet[2:4], 'big')
            received_data = packet[4:-2]
            trailer_id = int.from_bytes(packet[-2:], 'big')

            if packet_id == expected_packet_id:
                received_packets.append(received_data)
                packets_timestamps.append((packet_id, time.time()))
                expected_packet_id += 1

                # Send ACK for the received packet
                ACK = packet_id.to_bytes(2, 'big')
                server_socket.sendto(ACK, (server_ip, server_port))

                # If this is the last packet, break the loop
                if trailer_id == 0xFFFF:
                    break
            else:
                # Send ACK for the last correctly received packet
                ACK = (expected_packet_id - 1).to_bytes(2, 'big')
                server_socket.sendto(ACK, (server_ip, server_port))
        except timeout:
            print("Request time out")

    # Save received data to a file
    with open("received_file.png", "wb") as f:
        f.write(b''.join(received_packets))

    # Display file transfer information
    transfer_end_time = time.time()
    elapsed_time = transfer_end_time - transfer_start_time
    packets_count = len(received_packets)
    bytes_count = sum([len(packet) for packet in received_packets])
    print_transfer_info(transfer_start_time, transfer_end_time, elapsed_time, packets_count, bytes_count)

    # Plot packet ID vs time
    if plot_loss:
        packet_ids, timestamps = zip(*packets_timestamps)
        plt.plot(timestamps, packet_ids, 'ro', label='Received Packets')
        plt.xlabel('Time')
        plt.ylabel('Packet ID')
        plt.title('Packet ID vs Time')
        plt.legend()
        plt.show()

if __name__ == '__main__':
    params = load_parameters()
    kwargs = {'server_ip': params["SERVER"], 'server_port': params["receiver_port"]}
    while True:
        receiver(**kwargs)
        receive_another_file = input("Do you want to receive another file? (yes/no)(y/n): ")
        if receive_another_file.lower() not in ["yes", "y"]:
            break
