"""Synthetic shipment delay investigation; no dispatch or customer messages."""
import json
import urllib.request
from datetime import datetime

SHIPMENTS={"SHIP-DEMO-01":{"source":"shipment-demo-01","eta":"2026-10-12T12:00:00+00:00","as_of":"2026-10-12T13:00:00+00:00","delivered_at":None}}
EVENTS={"SHIP-DEMO-01":[{"source":"event-demo-01","occurred_at":"2026-10-12T10:00:00+00:00","type":"at_hub","note":"Synthetic hub scan; does not prove cause of delay"}]}


def utc_time(value):
    if not isinstance(value,str) or len(value)>50:raise ValueError("Timestamp must be a bounded ISO string")
    result=datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:raise ValueError("Timezone is required")
    return result


def assess(shipment,events):
    eta,as_of=utc_time(shipment["eta"]),utc_time(shipment["as_of"])
    observed=[event for event in events if utc_time(event["occurred_at"])<=as_of]
    observed.sort(key=lambda event:utc_time(event["occurred_at"]))
    delivered=shipment.get("delivered_at")
    if delivered is not None:
        delivered=utc_time(delivered)
        if delivered>as_of:raise ValueError("Delivered timestamp is after the observation snapshot")
    cutoff=delivered if delivered is not None else as_of
    seconds=max(0,(cutoff-eta).total_seconds())
    return {"source":"delay-assessment-demo-01","inputs":[shipment["source"]]+[e["source"] for e in observed],"status":"delivered_late" if delivered is not None and seconds else "delivered_on_time" if delivered is not None else "past_eta_delivery_unconfirmed" if seconds else "within_eta_delivery_unconfirmed","overdue_minutes":int(seconds//60),"last_observed_event":observed[-1] if observed else None,"cause":"unknown","snapshot":shipment["as_of"],"future_events_ignored":len(events)-len(observed)}


def tools():
    descriptions={"lookup_shipment":"Read synthetic promised ETA and fixed observation snapshot", "lookup_events":"Read synthetic carrier event records; events may not prove the reason for delay", "assess_delay":"Calculate overdue minutes using timezone-aware timestamps; delivered status requires explicit evidence"}
    return [{"type":"function","function":{"name":name,"description":text,"parameters":{"type":"object","properties":{"shipment_id":{"type":"string"}},"required":["shipment_id"],"additionalProperties":False}}} for name,text in descriptions.items()]


def execute(name,arguments,shipment_id):
    if name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments,dict) or set(arguments)!={"shipment_id"} or arguments["shipment_id"]!=shipment_id:raise ValueError("Invalid tool or cross-shipment arguments")
    item=SHIPMENTS.get(shipment_id)
    if not item:return []
    if name=="lookup_shipment":return [item]
    if name=="lookup_events":return EVENTS.get(shipment_id,[])
    return [assess(item,EVENTS.get(shipment_id,[]))]


def chat(messages):
    payload={"model":"qwen3:4b","messages":messages,"tools":tools(),"stream":False,"think":True,"options":{"temperature":0,"num_ctx":8192,"num_predict":2500}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)["message"]
