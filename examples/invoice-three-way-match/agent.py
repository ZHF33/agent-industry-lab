"""Synthetic invoice / purchase order / receipt review, no payments."""
import json
import urllib.request
from decimal import Decimal

ORDERS={"INV-DEMO-01":{"source":"po-demo-01","po_id":"PO-DEMO-01","sku":"ITEM-DEMO-01","quantity":10,"unit":"piece","currency":"CNY","unit_price":"12.50"}}
RECEIPTS={"INV-DEMO-01":{"source":"receipt-demo-01","po_id":"PO-DEMO-01","sku":"ITEM-DEMO-01","quantity":8,"unit":"piece"}}
INVOICES={"INV-DEMO-01":{"source":"invoice-demo-01","po_id":"PO-DEMO-01","sku":"ITEM-DEMO-01","quantity":10,"unit":"piece","currency":"CNY","unit_price":"12.50","line_total":"125.00"}}


def money(text):
    if not isinstance(text,str) or len(text)>32:raise ValueError("Money must be a bounded string")
    value=Decimal(text)
    if not value.is_finite() or not 0<=value<=Decimal("1000000000"):raise ValueError("Invalid money")
    return value


def match(order,receipt,invoice):
    for record in [order,receipt,invoice]:
        if type(record.get("quantity")) is not int or not 1<=record["quantity"]<=1000000:raise ValueError("Invalid quantity")
    issues=[]
    for key in ["po_id","sku","unit"]:
        if len({record[key] for record in [order,receipt,invoice]})!=1:issues.append(key+"_mismatch")
    if invoice["currency"]!=order["currency"]:issues.append("currency_mismatch")
    if invoice["quantity"]>receipt["quantity"]:issues.append("invoiced_above_received")
    if invoice["quantity"]>order["quantity"]:issues.append("invoiced_above_ordered")
    if invoice["currency"]==order["currency"] and money(invoice["unit_price"])!=money(order["unit_price"]):issues.append("unit_price_mismatch")
    calculated=money(invoice["unit_price"])*invoice["quantity"]
    if calculated!=money(invoice["line_total"]):issues.append("line_total_mismatch")
    return {"source":"match-demo-01","inputs":[order["source"],receipt["source"],invoice["source"]],"issues":issues,"calculated_line_total":str(calculated),"payment_authorized":False,"basis":"single line, before tax and freight; no currency conversion"}


def tools():
    descriptions={"lookup_order":"Read synthetic purchase order", "lookup_documents":"Read synthetic receipt and invoice records", "match_documents":"Compare single-line identity, quantities, currency, price and pre-tax line arithmetic; no payment authorization"}
    return [{"type":"function","function":{"name":n,"description":d,"parameters":{"type":"object","properties":{"invoice_id":{"type":"string"}},"required":["invoice_id"],"additionalProperties":False}}} for n,d in descriptions.items()]


def execute(name,arguments,invoice_id):
    if name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments,dict) or set(arguments)!={"invoice_id"} or arguments["invoice_id"]!=invoice_id:raise ValueError("Invalid tool scope")
    if invoice_id not in INVOICES:return []
    if name=="lookup_order":return [ORDERS[invoice_id]]
    if name=="lookup_documents":return [RECEIPTS[invoice_id],INVOICES[invoice_id]]
    return [match(ORDERS[invoice_id],RECEIPTS[invoice_id],INVOICES[invoice_id])]


def chat(messages):
    payload={"model":"qwen3:4b","messages":messages,"tools":tools(),"stream":False,"think":True,"options":{"temperature":0,"num_ctx":8192,"num_predict":2500}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)["message"]
