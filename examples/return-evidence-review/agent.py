"""Synthetic return evidence tools. Never authorizes refunds."""
import json
import urllib.request
from datetime import date

ORDERS={"RET-DEMO-01":{"source":"order-demo-01","delivered":"2026-10-01","requested":"2026-10-14","quantity":2}}
EVIDENCE={"RET-DEMO-01":{"source":"evidence-demo-01","photos_received":False,"reported_quantity":1,"note":"Synthetic damage report; unverified customer statement"}}
POLICY={"source":"policy-demo-01","window_days":14,"required":["photos_received"],"meaning":"Synthetic internal review checklist, not consumer law or refund entitlement"}


def assess(order,evidence):
    elapsed=(date.fromisoformat(order["requested"])-date.fromisoformat(order["delivered"])).days
    if elapsed<0:raise ValueError("Request before delivery")
    count=evidence["reported_quantity"]
    if type(count) is not int or not 1<=count<=order["quantity"]:raise ValueError("Invalid return quantity")
    return {"source":"assessment-demo-01","inputs":[order["source"],evidence["source"],POLICY["source"]],"elapsed_days":elapsed,"within_demo_window":elapsed<=POLICY["window_days"],"missing_evidence":[k for k in POLICY["required"] if evidence.get(k) is not True],"refund_authorized":False}


def tools():
    descriptions={"lookup_order":"Read synthetic delivery and request dates and quantities", "lookup_evidence":"Read synthetic reported damage and checklist evidence plus synthetic policy", "assess_return":"Calculate elapsed days and missing evidence; not a legal or refund determination"}
    return [{"type":"function","function":{"name":n,"description":d,"parameters":{"type":"object","properties":{"return_id":{"type":"string"}},"required":["return_id"],"additionalProperties":False}}} for n,d in descriptions.items()]


def execute(name,arguments,return_id):
    if name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments,dict) or set(arguments)!={"return_id"} or arguments["return_id"]!=return_id:raise ValueError("Invalid tool scope")
    if return_id not in ORDERS:return []
    if name=="lookup_order":return [ORDERS[return_id]]
    if name=="lookup_evidence":return [EVIDENCE[return_id],POLICY]
    return [assess(ORDERS[return_id],EVIDENCE[return_id])]


def chat(messages):
    payload={"model":"qwen3:4b","messages":messages,"tools":tools(),"stream":False,"think":True,"options":{"temperature":0,"num_ctx":8192,"num_predict":2500}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)["message"]
