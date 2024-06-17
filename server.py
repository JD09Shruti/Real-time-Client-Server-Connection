
import socket
import threading
import pandas as pd
from datetime import datetime
import time

# Initialize an empty DataFrame with the required columns
columns = [
    "Timestamp", "Client", "Status", "WiFi Status", "CPU Utilization", 
    "RAM Utilization", "HDD Temperature", "Number of Users", 
    "Download Speed", "Upload Speed"
]
data_frame = pd.DataFrame(columns=columns)
data_lock = threading.Lock()
clients = {}
clients_lock = threading.Lock()

def handle_client(client_socket, client_address):
    global data_frame
    client_ip = client_address[0]
    client_port = client_address[1]
    
    try:
        client_hostname = socket.gethostbyaddr(client_ip)[0]
    except socket.herror:
        client_hostname = client_ip  # Fallback to IP if hostname resolution fails

    if client_hostname == 'wdx5cg01089db.jdnet.deere.com' or client_hostname == '172.21.77.84':
        client_no = "My desktop"
    elif client_hostname == 'wpyn6959864d.jdnet.deere.com':
        client_no = "Client desktop"
    elif client_hostname == 'wpy9dh65535md.jdnet.deere.com':
        client_no = "5MVCS00"
    elif client_hostname == 'wpy8cc2043qvtdt.jdnet.deere.com':
        client_no = "5MVCS02"
    else:
        client_no = "unknown"

    client_name = f"{client_hostname}:{client_no}"
    print(f"Connection from {client_name}")

    global clients
    with clients_lock:
        clients[client_name] = {'socket': client_socket, 'last_update': time.time(), 'status': 'Online'}

    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                print(f"Connection from {client_name} lost")
                break
            
            # Prepare a dictionary to hold the parsed data
            update_data = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Client": client_name,
                "Status": "Online"
            }

            # Split the incoming data by a delimiter (e.g., newline or semicolon)
            attributes = data.split(';')
            for attribute in attributes:
                if attribute.startswith("WiFi Status:"):
                    update_data["WiFi Status"] = attribute.split(': ')[1]
                elif attribute.startswith("CPU Utilization:"):
                    update_data["CPU Utilization"] = attribute.split(': ')[1]
                elif attribute.startswith("HDD Temperature:"):
                    update_data["HDD Temperature"] = attribute.split(': ')[1]
                elif attribute.startswith("Number of Users:"):
                    update_data["Number of Users"] = attribute.split(': ')[1]
                elif attribute.startswith("Download Speed:"):
                    update_data["Download Speed"] = attribute.split(': ')[1]
                elif attribute.startswith("Upload Speed:"):
                    update_data["Upload Speed"] = attribute.split(': ')[1]
                elif attribute.startswith("RAM Utilization:"):
                    update_data["RAM Utilization"] = attribute.split(': ')[1]
                else:
                    print(f"Unrecognized attribute from {client_name}: {attribute}")

            # Update the DataFrame
            with data_lock:
                # Check if the client already exists in the DataFrame
                if client_name in data_frame["Client"].values:
                    # Update the existing row
                    for key in update_data:
                        data_frame.loc[data_frame["Client"] == client_name, key] = update_data[key]
                else:
                    # Add a new row
                    new_row = pd.DataFrame([update_data])
                    data_frame = pd.concat([data_frame, new_row], ignore_index=True)
                
                # Save the DataFrame to CSV
                data_frame.to_csv("server_data.csv", index=False)
                print(f"Data from {client_name} saved to CSV")

            with clients_lock:
                clients[client_name]['last_update'] = time.time()
            client_socket.send("Message from server: Data received".encode())

    except ConnectionResetError:
        print(f"Connection from {client_name} reset by client")
    except Exception as e:
        print(f"An error occurred with client {client_name}: {e}")
    finally:
        print(f"Closing connection from {client_name}")
        with clients_lock:
            if client_name in clients:
                clients[client_name]['status'] = 'Offline'
                
                clients[client_name]['last_update'] = time.time()

        # Update the DataFrame to mark the client as offline
        with data_lock:
            if client_name in data_frame["Client"].values:
                data_frame.loc[data_frame["Client"] == client_name, "Status"] = "Offline"
                data_frame.loc[data_frame["Client"] == client_name, "Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data_frame.to_csv("server_data.csv", index=False)
                print(f"Client {client_name} marked as offline and saved to CSV")
        
        client_socket.close()

def check_client_timeouts():
    global clients
    timeout = 60  # seconds
    while True:
        current_time = time.time()
        with clients_lock:
            for client_name in list(clients.keys()):
                if current_time - clients[client_name]['last_update'] > timeout:
                    print(f"Client {client_name} timed out.")
                    clients[client_name]['socket'].close()
                    clients[client_name]['status'] = 'Offline'

                    # Update the DataFrame to mark the client as offline
                    with data_lock:
                        if client_name in data_frame["Client"].values:
                            data_frame.loc[data_frame["Client"] == client_name, "Status"] = "Offline"
                            data_frame.loc[data_frame["Client"] == client_name, "Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            data_frame.to_csv("server_data.csv", index=False)
                            print(f"Client {client_name} marked as offline due to timeout and saved to CSV")

                    del clients[client_name]

        time.sleep(10)

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8000))
    server_socket.listen(5)
    print("Server is listening on hostname '0.0.0.0' and port 8000...")

    threading.Thread(target=check_client_timeouts, daemon=True).start()

    while True:
        try:
            client_socket, client_address = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.daemon = True
            client_thread.start()
        except Exception as e:
            print(f"An error occurred while accepting a client connection: {e}")

if __name__ == "__main__":
    start_server()
