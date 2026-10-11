"""Synthetic supplier quote comparison; read-only, no orders or messages."""
import json
import urllib.request
from decimal import Decimal, ROUND_HALF_UP

RFQS={"RFQ-DEMO-01":{"source":"rfq-demo-01","quantity":100,"unit":"piece","currency":"CNY","max_lead_days":7}}
QUOTES={"RFQ-DEMO-01":[
 {"source":"quote-demo-a","supplier":"DEMO-A","unit_price":"10.20","freight":"20.00","currency":"CNY","unit":"piece","lead_days":5},
 {"source":"quote-demo-b","supplier":"DEMO-B","unit_price":"9.90","freight":"80.00","currency":"CNY","unit":"piece","lead_days":9},
 {"source":"quote-demo-c","supplier":"DEMO-C","unit_price":"9.00","freight":None,"currency":"CNY","unit":"piece","lead_days":6},
 {"source":"quote-demo-d","supplier":"DEMO-D","unit_price":"1.50","freight":"2.00","currency":"USD","unit":"piece","lead_days":4}
]}


def money(value):
    if not isinstance(value,str) or len(value)>32:raise ValueError("Money must be a bounded decimal string")
    result=Decimal(value)
    if not result.is_finite() or result<0 or result>Decimal("1000000000"):raise ValueError("Invalid monetary amount")
    return result


def compare(rfq,quotes):
    quantity=rfq["quantity"]
    if type(quantity) is not int or not 1<=quantity<=1000000:raise ValueError("Invalid quantity")
    rows=[]
    for quote in quotes:
        reasons=[]
        if quote.get("currency")!=rfq["currency"]:reasons.append("currency_mismatch")
        if quote.get("unit")!=rfq["unit"]:reasons.append("unit_mismatch")
        if quote.get("freight") is None:reasons.append("freight_missing")
        if quote.get("unit_price") is None:reasons.append("unit_price_missing")
        row={"quote_source":quote["source"],"supplier":quote["supplier"],"currency":quote.get("currency"),"total_before_tax":None,"issues":reasons,"within_lead_time":type(quote.get("lead_days")) is int and 0<=quote["lead_days"]<=rfq["max_lead_days"]}
        if not reasons:
            total=(money(quote["unit_price"])*quantity+money(quote["freight"])).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
            row["total_before_tax"]=str(total)
        rows.append(row)
    return rows


def tools():
    descriptions={"lookup_request":"Read synthetic procurement quantity, currency, unit and deadline", "lookup_quotes":"Read supplier quote sources, prices, shipping and delivery", "compare_costs":"Compute comparable pre-tax totals with Decimal; flag missing shipping, currency and unit mismatch"}
    return [{"type":"function","function":{"name":name,"description":text,"parameters":{"type":"object","properties":{"rfq_id":{"type":"string"}},"required":["rfq_id"],"additionalProperties":False}}} for name,text in descriptions.items()]


def execute(name,arguments,rfq_id):
    if name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments,dict) or set(arguments)!={"rfq_id"} or arguments["rfq_id"]!=rfq_id:raise ValueError("Invalid tool or cross-request arguments")
    rfq=RFQS.get(rfq_id)
    if not rfq:return []
    if name=="lookup_request":return [rfq]
    if name=="lookup_quotes":return QUOTES.get(rfq_id,[])
    return [{"source":"comparison-demo-01","inputs":[rfq["source"]]+[q["source"] for q in QUOTES.get(rfq_id,[])],"rows":compare(rfq,QUOTES.get(rfq_id,[])),"basis":"quantity * unit price + freight, before tax; no currency conversion"}]


def chat(messages):
    payload={"model":"qwen3:4b","messages":messages,"tools":tools(),"stream":False,"think":True,"options":{"temperature":0,"num_ctx":8192,"num_predict":2500}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)["message"]
