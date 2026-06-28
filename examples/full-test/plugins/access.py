class AccessResolver:
    def can_access(self, ctx: dict, node_id: str) -> bool:
        # Local-dev default: allow everything. Replace with real policy
        # (inspect `ctx` for user role / tier, decide per `node_id`).
        return True
