import socket
import psutil
import time
import subprocess
import threading
import wmi
import pythoncom
import speedtest

def check_wifi_connection():
    try:
        subprocess.check_output("ping 204.53.210.50", shell=True)
        return "Online"
    except subprocess.CalledProcessError:
        return "Offline"

def get_monitor_serial_number():
    powershell_command = (
        r"Get-WmiObject -Namespace root\wmi -Class WmiMonitorID | ForEach-Object {($_.SerialNumberID -ne 0 | foreach {[char]$_}) -join ''}"
    )

    result = subprocess.run(["powershell", "-Command", powershell_command], capture_output=True, text=True)

    if result.returncode == 0:
        serial_numbers = [line for line in result.stdout.split('\n') if line.strip()]
        if serial_numbers:
            return serial_numbers[0]  # Return the first serial number found
        else:
            return "No monitor serial numbers found."
    else:
        return f"Error: {result.stderr}"

def get_hdd_temperature():
    try:
        pythoncom.CoInitialize()  # Initialize COM
        c = wmi.WMI(namespace="root\\wmi")  # Corrected escape sequence
        temperature_info = c.MSAcpi_ThermalZoneTemperature()
        for temp in temperature_info:
            return f"{temp.CurrentTemperature / 10.0 - 273.15:.2f}°C"
    except wmi.x_wmi as e:
        return f"Error retrieving HDD temperature: {e}"
    except Exception as e:
        return f"Unexpected error retrieving HDD temperature: {e}"
    finally:
        pythoncom.CoUninitialize()  # Uninitialize COM

import os
import glob

def get_number_of_users():
    try:
        users_dir = "C:\\Users"
        default_users = {"All Users", "Default", "Default User", "defaultuser0", "Public"}
        users = [name for name in os.listdir(users_dir) if os.path.isdir(os.path.join(users_dir, name)) and name not in default_users]
        return f"{len(users)}"
    except Exception as e:
        return f"Error retrieving number of users: {e}"


def get_wifi_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps
        return f"{download_speed:.2f} Mbps", f"{upload_speed:.2f} Mbps"
    except Exception as e:
        return f"Error retrieving WiFi speed: {e}", f"Error retrieving WiFi speed: {e}"

def get_ram_utilization():
    try:
        memory = psutil.virtual_memory()
        return f"{memory.percent}%"
    except Exception as e:
        return f"Error retrieving RAM utilization: {e}"

def client_process(client_socket):
    pythoncom.CoInitialize()  # Initialize COM in the main client thread
    try:
        while True:
            cpu_percent = psutil.cpu_percent()
            hdd_temperature = get_hdd_temperature()
            number_of_users = get_number_of_users()
            wifi_status = check_wifi_connection()
            download_speed, upload_speed = get_wifi_speed()
            ram_utilization = get_ram_utilization()

            data = (
                f"WiFi Status: {wifi_status};"
                f"CPU Utilization: {cpu_percent}%;"
                f"RAM Utilization: {ram_utilization};"
                f"HDD Temperature: {hdd_temperature};"
                f"Number of Users: {number_of_users};"
                f"Download Speed: {download_speed};"
                f"Upload Speed: {upload_speed}"
            )

            client_socket.send(data.encode())
            server_message = client_socket.recv(1024).decode()
            print(f"Server message: {server_message}")

            time.sleep(15)

    except (ConnectionResetError, ConnectionAbortedError) as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pythoncom.CoUninitialize()  # Uninitialize COM

def connect_to_server(server_hostname, server_port):
    client_socket = None
    while client_socket is None:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((server_hostname, server_port))
            print(f"Connected to server at {server_hostname}:{server_port}")
        except (socket.error, ConnectionRefusedError) as e:
            print(f"Connection failed: {e}. Retrying in 15 seconds...")
            time.sleep(15)
    return client_socket

def start_client(server_hostname, server_port):
    while True:
        client_socket = connect_to_server(server_hostname, server_port)
        client_thread = threading.Thread(target=client_process, args=(client_socket,))
        client_thread.start()

        # Keep the main thread alive
        client_thread.join()

if __name__ == "__main__":
    server_hostname = 'fsanpyapp26'
    server_port = 8000
    start_client(server_hostname, server_port)
