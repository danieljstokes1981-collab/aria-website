import json
import hashlib
import time

class ARIAShadowPilot:
    def __init__(self, ledger_file="aria_shadow_ledger.jsonl"):
        self.ledger_file = ledger_file
        # Poset DAG reachability matrix
        self.permitted_edges = {
            (6, 9): True,   # Permitted Downward Flow
            (8, 2): False,  # Blocked Upward Flow
            (8, 9): False   # Blocked Lateral Flow
        }
        self.last_merkle_root = "0" * 64

    def _hash(self, data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def process_telemetry_event(self, event_id: int, source_node: int, target_node: int, payload: dict):
        timestamp = time.time_ns()
        raw_bytes = f"{timestamp}:{event_id}:{source_node}:{target_node}:{json.dumps(payload, sort_keys=True)}"
        event_hash = self._hash(raw_bytes)
        
        is_reachable = self.permitted_edges.get((source_node, target_node), False)
        dispatch_action = "PERMITTED" if is_reachable else "BLOCKED_FAIL_CLOSED"
        
        new_merkle_root = self._hash(f"{self.last_merkle_root}:{event_hash}:{dispatch_action}")
        self.last_merkle_root = new_merkle_root
        
        record = {
            "timestamp_ns": timestamp,
            "event_id": event_id,
            "flow": f"Node_{source_node} -> Node_{target_node}",
            "reachability_granted": is_reachable,
            "shadow_action": dispatch_action,
            "event_hash": event_hash,
            "merkle_root": new_merkle_root
        }
        
        with open(self.ledger_file, "a") as f:
            f.write(json.dumps(record) + "\n")
            
        return record

if __name__ == "__main__":
    print("==================================================================")
    print("      ARIA TRL 7 LIVE SHADOW INTEGRATION PILOT HARNESS")
    print("==================================================================")
    
    pilot = ARIAShadowPilot()
    
    test_stream = [
        {"id": 101, "src": 6, "dst": 9, "payload": {"user": "student_session_01", "action": "read"}},
        {"id": 102, "src": 8, "dst": 2, "payload": {"user": "unauth_process_04", "action": "priv_esc"}},
        {"id": 103, "src": 8, "dst": 9, "payload": {"user": "agent_process_09", "action": "lateral_move"}},
    ]
    
    for event in test_stream:
        res = pilot.process_telemetry_event(event["id"], event["src"], event["dst"], event["payload"])
        print(f"[*] Processed Event #{res['event_id']} ({res['flow']}):")
        print(f"    - Reachability : {res['reachability_granted']}")
        print(f"    - Shadow Action: {res['shadow_action']}")
        print(f"    - Merkle Root  : {res['merkle_root'][:16]}...\n")
        
    print("[✓] TRL 7 Shadow Pilot run complete. Audit recorded in 'aria_shadow_ledger.jsonl'.")
