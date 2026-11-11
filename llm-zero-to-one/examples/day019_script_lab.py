def difference(requested, issued, returned):
    net = issued - returned
    return net - requested


if __name__ == "__main__":
    print(difference(10, 8, 1))
