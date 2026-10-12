---
name: shipment-delay-investigation
description: Investigate synthetic shipment delays with timezone-aware evidence and human review.
---

1. Submit synthetic case_id, shipment_id and description using the README configuration. Keep keys local.
2. Inspect ETA, fixed observation snapshot, timestamp offsets and delay_assessment. Do not treat events after the snapshot as known at that time.
3. Missing delivery evidence means delivery unconfirmed. A hub scan cannot prove the cause. Humans must verify carrier and recipient records.
4. Preserve thread_id and explicitly approve/reject a recommendation. Do not dispatch, update promises, compensate or contact customers.
5. Do not blindly retry ambiguous submissions. Store raw outputs locally and never publish real shipment records. Do not start services unless requested.
