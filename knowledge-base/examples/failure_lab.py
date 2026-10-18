def suggest(method, observation):
    if method not in {"GET", "HEAD"} and observation == "timeout":
        return "reconcile"
    if method in {"GET", "HEAD"} and observation in {429, 502, 503, 504, "timeout"}:
        return "review_retry"
    return "investigate"


if __name__ == "__main__":
    print("GET 503", suggest("GET", 503))
    print("POST timeout", suggest("POST", "timeout"))
    print("POST 403", suggest("POST", 403))
