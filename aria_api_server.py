from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import hashlib
import time
import uvicorn

app = FastAPI(title="ARIA Out-of-Band Governance Substrate")

class TelemetryEvent(BaseModel):
    event_id: int
    source_node: int
    target_node: int
    payload: dict

class ARIASubstrate:
    def __init__(self, ledger_file="aria_shadow_ledger.jsonl"):
        self.ledger_file = ledger_file
        self.permitted_edges = {
            (6, 9): True,   # Permitted Downward Flow
            (8, 2): False,  # Blocked Upward Flow
            (8, 9): False   # Blocked Lateral Flow
        }
        self.last_merkle_root = "0" * 64

    def _hash(self, data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def process_event(self, event: TelemetryEvent):
        timestamp = time.time_ns()
        raw_bytes = f"{timestamp}:{event.event_id}:{event.source_node}:{event.target_node}:{json.dumps(event.payload, sort_keys=True)}"
        event_hash = self._hash(raw_bytes)
        
        is_reachable = self.permitted_edges.get((event.source_node, event.target_node), False)
        dispatch_action = "PERMITTED" if is_reachable else "BLOCKED_FAIL_CLOSED"
        
        new_merkle_root = self._hash(f"{self.last_merkle_root}:{event_hash}:{dispatch_action}")
        self.last_merkle_root = new_merkle_root
        
        record = {
            "timestamp_ns": timestamp,
            "event_id": event.event_id,
            "flow": f"Node_{event.source_node} -> Node_{event.target_node}",
            "reachability_granted": is_reachable,
            "shadow_action": dispatch_action,
            "event_hash": event_hash,
            "merkle_root": new_merkle_root
        }
        
        with open(self.ledger_file, "a") as f:
            f.write(json.dumps(record) + "\n")
            
        return record

substrate = ARIASubstrate()

@app.post("/evaluate")
async def evaluate_event(event: TelemetryEvent):
    result = substrate.process_event(event)
    if not result["reachability_granted"]:
        raise HTTPException(status_code=403, detail="Layer 7 Poset Violation: Execution Blocked Fail-Closed")
    return {"status": "SUCCESS", "record": result}

if __name__ == "__main__":
    print("[*] Starting ARIA Out-of-Band Governance API on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
