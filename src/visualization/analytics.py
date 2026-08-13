def _cluster_members(cluster_id: int) -> list[int]:
        """Return the leaf indices that belong to a cluster node iteratively."""
        members = []
        stack = [cluster_id]
        while stack:
            curr_id = stack.pop()
            if curr_id < n_leaves:
                members.append(int(curr_id))
            else:
                row = linkage_matrix[curr_id - n_leaves]
                stack.append(int(row[0]))
                stack.append(int(row[1]))
        return members
