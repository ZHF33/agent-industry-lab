"""Synthetic API failure evidence tools. No external calls or retries."""
import json
import urllib.request

INCIDENTS={"API-DEMO-01":{"source":"incident-demo-01","operation":"submit_order","method":"POST","idempotency_supported":False}}
OBSERVATIONS={"API-DEMO-01":[{"source":"response-demo-01","kind":"http","status":503},{"source":"response-demo-02","kind":"timeout","status":None}]}
POLICY={"source":"retry-policy-demo-01","read_only_methods":["GET","HEAD"],"transient_statuses":[429,502,503,504],"meaning":"Synthetic triage guidance; recommendations do not execute retries"}


def classify(incident,observations):
    rows=[]
    read_only=incident["method"] in POLICY["read_only_methods"]
    for event in observations:
        kind,status=event["kind"],event.get("status")
        if kind not in {"http","timeout","connection_error"}:raise ValueError("Invalid observation kind")
        if kind=="http" and (type(status) is not int or not 100<=status<=599):raise ValueError("Invalid HTTP status")
        category="outcome_unknown" if kind=="timeout" else "transport_error" if kind=="connection_error" else "authentication" if status==401 else "authorization_or_policy" if status==403 else "rate_limit" if status==429 else "server_error" if status>=500 else "client_request" if status>=400 else "response_received"
        candidate=kind!="http" or status in POLICY["transient_statuses"]
        rows.append({"source":event["source"],"category":category,"retry_candidate_for_human_review":candidate and read_only,"reconcile_before_resubmitting":not read_only,"automatic_retry":False})
    return {"source":"failure-triage-demo-01","inputs":[incident["source"],POLICY["source"]]+[e["source"] for e in observations],"rows":rows,"root_cause":"unknown","business_success_confirmed":False,"note":"This minimal policy only suggests reviewing retries for GET/HEAD; writes always require reconciliation and a separate idempotency design"}


def tools():
    descriptions={"lookup_incident":"Read synthetic failed operation and HTTP method", "lookup_observations":"Read synthetic HTTP/timeout evidence and retry policy", "classify_failures":"Classify errors and uncertain writes without executing retry or claiming root cause"}
    return [{"type":"function","function":{"name":n,"description":d,"parameters":{"type":"object","properties":{"incident_id":{"type":"string"}},"required":["incident_id"],"additionalProperties":False}}} for n,d in descriptions.items()]


def execute(name,arguments,incident_id):
    if name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments,dict) or set(arguments)!={"incident_id"} or arguments["incident_id"]!=incident_id:raise ValueError("Invalid tool scope")
    if incident_id not in INCIDENTS:return []
    if name=="lookup_incident":return [INCIDENTS[incident_id]]
    if name=="lookup_observations":return OBSERVATIONS[incident_id]+[POLICY]
    return [classify(INCIDENTS[incident_id],OBSERVATIONS[incident_id])]


def chat(messages):
    payload={"model":"qwen3:4b","messages":messages,"tools":tools(),"stream":False,"think":True,"options":{"temperature":0,"num_ctx":8192,"num_predict":2500}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)["message"]
