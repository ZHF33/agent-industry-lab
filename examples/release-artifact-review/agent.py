"""Synthetic release artifact integrity review; no filesystem access or deployment."""
import hashlib
import json
import urllib.request

EXPECTED={"app.txt":b"synthetic build v1\n","config.txt":b"synthetic config approved\n"}
ACTUAL={"app.txt":b"synthetic build v1\n","config.txt":b"synthetic config changed\n","extra.txt":b"synthetic unexpected artifact\n"}
RELEASE="REL-DEMO-01"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def verify(expected,actual):
    entries=[]
    for name in sorted(set(expected)|set(actual)):
        status="unexpected" if name not in expected else "missing" if name not in actual else "match" if digest(expected[name])==digest(actual[name]) else "mismatch"
        entries.append({"name":name,"status":status,"expected_sha256":digest(expected[name]) if name in expected else None,"actual_sha256":digest(actual[name]) if name in actual else None})
    return {"source":"integrity-demo-01","inputs":["manifest-demo-01","artifacts-demo-01"],"entries":entries,"all_expected_match":bool(expected) and all(row["status"]=="match" for row in entries),"authenticity_verified":False}


def tools():
    descriptions={"lookup_manifest":"Read the synthetic approved artifact baseline; it is an assumed trusted baseline, not a signed manifest", "lookup_artifacts":"Read synthetic submitted artifact names, sizes and digests; never accepts file paths", "verify_hashes":"Compare SHA-256 digests and flag missing, unexpected or mismatched artifacts; hashes do not establish publisher authenticity"}
    return [{"type":"function","function":{"name":name,"description":text,"parameters":{"type":"object","properties":{"release_id":{"type":"string"}},"required":["release_id"],"additionalProperties":False}}} for name,text in descriptions.items()]


def execute(name,arguments,release_id):
    if name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments,dict) or set(arguments)!={"release_id"} or arguments["release_id"]!=release_id:raise ValueError("Invalid tool or cross-release arguments")
    if release_id!=RELEASE:return []
    if name=="lookup_manifest":return [{"source":"manifest-demo-01","artifacts":[{"name":n,"sha256":digest(v)} for n,v in EXPECTED.items()]}]
    if name=="lookup_artifacts":return [{"source":"artifacts-demo-01","artifacts":[{"name":n,"bytes":len(v),"sha256":digest(v)} for n,v in ACTUAL.items()]}]
    return [verify(EXPECTED,ACTUAL)]


def chat(messages):
    payload={"model":"qwen3:4b","messages":messages,"tools":tools(),"stream":False,"think":True,"options":{"temperature":0,"num_ctx":8192,"num_predict":2500}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)["message"]
