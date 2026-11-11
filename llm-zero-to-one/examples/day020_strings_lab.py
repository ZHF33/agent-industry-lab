job_code = "00123"
snapshot = job_code
job_code = "00999"
print(job_code, snapshot)
print(len(snapshot), len(str(int(snapshot))))

for value in (snapshot, None, 123):
    if value is None:
        print("missing")
    elif isinstance(value, str) and len(value) == 5 and value.isascii() and value.isdecimal():
        print("valid")
    else:
        print("invalid")
