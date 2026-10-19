"""Synthetic alert grouping; never suppresses, closes or routes real alerts."""
import json
import urllib.request
from collections import Counter

BATCHES={"ALERT-DEMO-01":{"source":"batch-demo-01","window":"fixed synthetic observation batch","events":[
 {"source":"alert-record-demo-01","event_id":"E-1","service":"demo-api","code":"TIMEOUT","severity":"warning"},
 {"source":"alert-record-demo-02","event_id":"E-1","service":"demo-api","code":"TIMEOUT","severity":"warning"},
 {"source":"alert-record-demo-03","event_id":"E-2","service":"demo-api","code":"TIMEOUT","severity":"warning"},
 {"source":"alert-record-demo-04","event_id":"E-3","service":"demo-worker","code":"QUEUE_DEPTH","severity":"critical"}]}}
POLICY={"source":"group-policy-demo-01","key":["service","code","severity"],"rule":"Same event ID plus same payload is duplicate delivery; different event IDs remain separate observations, not proven same incident"}


def group_events(events):
    ids={};conflicts=set();duplicates=0
    for event in events:
        if not all(isinstance(event.get(k),str) and event[k].strip() for k in ["source","event_id","service","code","severity"]):raise ValueError("Invalid event fields")
        payload=tuple(event[k] for k in POLICY["key"]);eid=event["event_id"]
        if eid not in ids:ids[eid]=payload
        elif ids[eid]!=payload:conflicts.add(eid)
        else:duplicates+=1
    counts=Counter(payload for eid,payload in ids.items() if eid not in conflicts)
    return {"source":"grouping-demo-01","inputs":[POLICY["source"]]+[e["source"] for e in events],"received_records":len(events),"duplicate_deliveries":duplicates,"conflicting_event_ids":sorted(conflicts),"groups":[{"service":k[0],"code":k[1],"severity":k[2],"unique_events":v} for k,v in sorted(counts.items())],"alerts_suppressed":False,"root_cause":"unknown"}


def tools():
    descriptions={"lookup_batch":"Read fixed synthetic alert batch metadata", "lookup_events":"Read synthetic alert records and grouping policy", "group_alerts":"Deduplicate same-ID same-payload deliveries, flag conflicting IDs, group remaining observations; never proves incident identity"}
    return [{"type":"function","function":{"name":n,"description":d,"parameters":{"type":"object","properties":{"batch_id":{"type":"string"}},"required":["batch_id"],"additionalProperties":False}}} for n,d in descriptions.items()]


def execute(name,arguments,batch_id):
    if name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments,dict) or set(arguments)!={"batch_id"} or arguments["batch_id"]!=batch_id:raise ValueError("Invalid tool scope")
    batch=BATCHES.get(batch_id)
    if not batch:return []
    if name=="lookup_batch":return [{"source":batch["source"],"window":batch["window"],"record_count":len(batch["events"])}]
    if name=="lookup_events":return batch["events"]+[POLICY]
    return [group_events(batch["events"])]


def chat(messages):
    payload={"model":"qwen3:4b","messages":messages,"tools":tools(),"stream":False,"think":True,"options":{"temperature":0,"num_ctx":8192,"num_predict":2500}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)["message"]
