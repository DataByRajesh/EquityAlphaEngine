"""
Test IP/port connectivity.

This script tests connectivity to a specified IP and port.
Usage: python test_ip_port_connection.py <ip> <port>
"""

import socket
import sys

def test_connection(ip, port):
    """Test connection to the specified IP and port."""
    try:
        with socket.create_connection((ip, port), timeout=5) as conn:
            print(f"Successfully connected to {ip}:{port}")
            return True
    except Exception as e:
        print(f"Failed to connect to {ip}:{port}. Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test_ip_port_connection.py <ip> <port>")
        sys.exit(1)
    
    ip = sys.argv[1]
    port = int(sys.argv[2])
    success = test_connection(ip, port)
    if not success:
        sys.exit(1)
