"""Synthetic sensor-feed quality triage; never controls equipment."""
import json
import urllib.request
from datetime import datetime

FEEDS={"FEED-DEMO-01":{"source":"feed-demo-01","unit":"celsius","interval_seconds":60,"snapshot":"2026-10-15T12:03:00+00:00","min":-20,"max":100}}
READINGS={"FEED-DEMO-01":[{"source":"reading-demo-01","time":"2026-10-15T12:00:00+00:00","value":22,"unit":"celsius"},{"source":"reading-demo-02","time":"2026-10-15T12:01:00+00:00","value":999,"unit":"celsius"}]}


def timestamp(text):
    value=datetime.fromisoformat(text)
    if value.tzinfo is None or value.utcoffset() is None:raise ValueError("Timezone required")
    return value


def assess(feed,readings):
    now=timestamp(feed["snapshot"]); issues=[];valid=[]
    for row in readings:
        when=timestamp(row["time"])
        if when>now:issues.append({"source":row["source"],"type":"future_timestamp"});continue
        valid.append(when)
        value=row.get("value")
        if row.get("unit")!=feed["unit"]:issues.append({"source":row["source"],"type":"unit_mismatch"})
        if type(value) not in (int,float) or not feed["min"]<=value<=feed["max"]:issues.append({"source":row["source"],"type":"invalid_range"})
    age=(now-max(valid)).total_seconds() if valid else None
    if age is None or age>feed["interval_seconds"]:issues.append({"source":feed["source"],"type":"stale_or_missing"})
    return {"source":"quality-demo-01","inputs":[feed["source"]]+[r["source"] for r in readings],"issues":issues,"latest_age_seconds":age,"cause":"unknown","equipment_failure_confirmed":False}


def tools():
    descriptions={"lookup_feed":"Read synthetic feed interval, range and unit contract", "lookup_readings":"Read synthetic sensor observations", "assess_quality":"Compute stale feed, invalid range, future timestamp and unit mismatch flags; no equipment diagnosis"}
    return [{"type":"function","function":{"name":n,"description":d,"parameters":{"type":"object","properties":{"feed_id":{"type":"string"}},"required":["feed_id"],"additionalProperties":False}}} for n,d in descriptions.items()]


def execute(name,arguments,feed_id):
    if name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments,dict) or set(arguments)!={"feed_id"} or arguments["feed_id"]!=feed_id:raise ValueError("Invalid tool scope")
    if feed_id not in FEEDS:return []
    if name=="lookup_feed":return [FEEDS[feed_id]]
    if name=="lookup_readings":return READINGS[feed_id]
    return [assess(FEEDS[feed_id],READINGS[feed_id])]


def chat(messages):
    payload={"model":"qwen3:4b","messages":messages,"tools":tools(),"stream":False,"think":True,"options":{"temperature":0,"num_ctx":8192,"num_predict":2500}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)["message"]
