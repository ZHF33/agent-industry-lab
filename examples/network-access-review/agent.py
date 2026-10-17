"""Synthetic network access request review; no scans or firewall changes."""
import json
import urllib.request
from ipaddress import ip_address,ip_network

REQUESTS={"NET-DEMO-01":{"source":"request-demo-01","destination":"203.0.113.10","port":5432,"protocol":"tcp","reason":"Synthetic database access request"}}
ASSETS={"NET-DEMO-01":{"source":"asset-demo-01","owner":"demo-platform-team","environment":"demo"}}
POLICY={"source":"policy-demo-01","allowed_network":"192.0.2.0/24","allowed_ports":[443],"protocol":"tcp"}


def assess(request,policy):
    address=ip_address(request["destination"]);network=ip_network(policy["allowed_network"])
    port=request["port"]
    if type(port) is not int or not 1<=port<=65535:raise ValueError("Invalid port")
    issues=[]
    if address.version!=network.version or address not in network:issues.append("destination_outside_demo_scope")
    if port not in policy["allowed_ports"]:issues.append("port_not_in_demo_policy")
    if request["protocol"]!=policy["protocol"]:issues.append("protocol_mismatch")
    return {"source":"network-review-demo-01","inputs":[request["source"],policy["source"]],"issues":issues,"firewall_changed":False,"access_authorized":False,"basis":"synthetic exact IP, protocol and port checks, not complete network security review"}


def tools():
    descriptions={"lookup_request":"Read a synthetic network access request", "lookup_policy":"Read synthetic network policy and asset owner", "assess_access":"Compare literal IP destination, port and protocol to synthetic scope; does not authorize access"}
    return [{"type":"function","function":{"name":n,"description":d,"parameters":{"type":"object","properties":{"request_id":{"type":"string"}},"required":["request_id"],"additionalProperties":False}}} for n,d in descriptions.items()]


def execute(name,arguments,request_id):
    if name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments,dict) or set(arguments)!={"request_id"} or arguments["request_id"]!=request_id:raise ValueError("Invalid tool scope")
    if request_id not in REQUESTS:return []
    if name=="lookup_request":return [REQUESTS[request_id]]
    if name=="lookup_policy":return [POLICY,ASSETS[request_id]]
    return [assess(REQUESTS[request_id],POLICY)]


def chat(messages):
    payload={"model":"qwen3:4b","messages":messages,"tools":tools(),"stream":False,"think":True,"options":{"temperature":0,"num_ctx":8192,"num_predict":2500}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)["message"]
