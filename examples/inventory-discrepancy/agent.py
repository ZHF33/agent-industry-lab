"""Synthetic warehouse reconciliation tools; never updates stock."""
import json
import urllib.request

DATA = {
    "SKU-DEMO-01": {"book": 100, "counted": 94, "unit": "piece", "snapshot": "stock-demo-01", "count_source": "count-demo-01", "movements": [{"source": "movement-demo-01", "quantity": -6, "posting_status": "pending", "note": "Synthetic outbound record; not proof of cause"}]}
}


def tools():
    descriptions = {"lookup_stock": "Read synthetic book stock and physical count, same snapshot and unit", "lookup_movements": "Read recent synthetic movements; do not assume pending movements explain a discrepancy", "calculate_difference": "Compute physical minus book quantity with exact integer arithmetic"}
    return [{"type": "function", "function": {"name": name, "description": text, "parameters": {"type": "object", "properties": {"sku": {"type": "string"}}, "required": ["sku"], "additionalProperties": False}}} for name,text in descriptions.items()]


def execute(name, arguments, sku):
    if name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments,dict) or set(arguments)!={"sku"} or arguments["sku"]!=sku:
        raise ValueError("Invalid tool or cross-item arguments")
    item=DATA.get(sku)
    if not item:return []
    if name=="lookup_stock":
        return [{"source":item["snapshot"],"book":item["book"],"unit":item["unit"]},{"source":item["count_source"],"counted":item["counted"],"unit":item["unit"]}]
    if name=="lookup_movements":return item["movements"]
    return [{"source":"difference-demo-01","difference":item["counted"]-item["book"],"formula":"physical minus book","inputs":[item["snapshot"],item["count_source"]],"unit":item["unit"]}]


def chat(messages):
    payload={"model":"qwen3:4b","messages":messages,"tools":tools(),"stream":False,"think":True,"options":{"temperature":0,"num_ctx":8192,"num_predict":2500}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)["message"]
