package logline.authz

default allow = false

# Default deny reason (useful for debugging)
default reasons = ["No specific allow rule matched or prerequisite failed"]

# --- Helper: Check Role ---
has_role(required_roles) {
    # Input expects claims from JWT now
    provided_roles := object.get(input.claims, "roles", []) # Get roles, default to empty list
    count({role | role := provided_roles[_]; required_roles[role]}) > 0
}

# --- Rule: POST /gateway/process ---
allow {
    input.path == ["gateway", "process"]
    input.method == "POST"
    input.claims.sub # Ensure user is authenticated (sub claim exists)
    # Add role check if needed, e.g., only 'staff' can use gateway?
    # has_role({"staff", "admin"})
    reasons := [] # Clear reasons on success
} else = r {
    input.path == ["gateway", "process"]; input.method == "POST"
    msgs := []
    not input.claims.sub -> msgs := array.concat(msgs, ["User authentication required."])
    # not has_role({"staff", "admin"}) -> msgs := array.concat(msgs, ["User role not permitted for gateway."])
    r := {"reasons": msgs}
}

# --- Rule: POST /actions/registrar_venda ---
allow {
    input.path == ["actions", "registrar_venda"]
    input.method == "POST"
    # Example: Allow staff or system roles
    has_role({"staff", "admin", "system"})
    # Add policy checks on input.body if needed
    # input.body.channel == "internal" # Example
    reasons := []
} else = r {
    input.path == ["actions", "registrar_venda"]; input.method == "POST"
    msgs := []
    not has_role({"staff", "admin", "system"}) -> msgs := array.concat(msgs, ["User role not permitted."])
    r := {"reasons": msgs}
}

# --- Rule: Deny Log Deletion ---
# Needs path adjusted based on actual API structure for timeline/logs
# Assuming timeline path is /timeline/{log_id}
allow = false {
    input.method == "DELETE"
    input.path[0] == "timeline"
    count(input.path) == 2 # Path looks like ["timeline", "some_id"]
    reasons := ["Deleting logs is forbidden."]
}

# --- Final Decision ---
# Use the reasons from the first failing block that provides them
result = {"allow": false, "reasons": r.reasons} {
    some block_index
    rule_block_result := [allow | else = _][block_index]
    rule_block_result == false
    some r
    [allow | else = r][block_index]
} else = {"allow": allow, "reasons": reasons} { # Use default reasons if no specific block failed with reasons
    true
}