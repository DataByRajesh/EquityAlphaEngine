import socket

def test_connection(ip, port):
    try:
        with socket.create_connection((ip, port), timeout=5) as conn:
            print(f"Successfully connected to {ip}:{port}")
    except Exception as e:
        print(f"Failed to connect to {ip}:{port}. Error: {e}")

if __name__ == "__main__":
    # Replace with your IP and port
    ip = "34.39.5.6"
    port = 5432
    test_connection(ip, port)
