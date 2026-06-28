class AccessResolver:
    def can_access(self, ctx: dict, node_id: str) -> bool:
        raise NotImplementedError
