from ipaddress import ip_address, ip_network


if __name__ == "__main__":
    network = ip_network("192.0.2.0/24")
    print("inside", ip_address("192.0.2.10") in network)
    print("outside", ip_address("203.0.113.10") in network)
