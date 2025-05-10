package logline.authz

test_staff_can_create_sale_action {
    allow with input as {
        "path": ["actions", "registrar_venda"],
        "method": "POST",
        "claims": {"sub": "staff@example.com", "uid": "staff_id_123", "roles": ["staff"]},
        "request_body": {"items": [{"product_id":"p1","quantity":1}], "channel":"test"}
    }
}

test_customer_cannot_create_sale_action_directly {
    not allow with input as {
        "path": ["actions", "registrar_venda"],
        "method": "POST",
        "claims": {"sub": "cust@example.com", "uid": "cust_id_789", "roles": ["customer"]},
        "request_body": {"items": [{"product_id":"p1","quantity":1}], "channel":"test"}
    }
}

test_manager_can_corrigir_evento {
    allow with input as {
        "path": ["actions", "corrigir_evento"],
        "method": "POST",
        "claims": {"sub": "manager@example.com", "uid": "mgr_123", "roles": ["manager"]},
        "request_body": {"target_event_id": "evt_abc", "motivo_correcao": "erro", "corrected_data_payload": {"foo": "bar"}}
    }
}

test_customer_cannot_corrigir_evento {
    not allow with input as {
        "path": ["actions", "corrigir_evento"],
        "method": "POST",
        "claims": {"sub": "customer@example.com", "uid": "cust_abc", "roles": ["customer"]},
        "request_body": {"target_event_id": "evt_abc", "motivo_correcao": "erro", "corrected_data_payload": {"foo": "bar"}}
    }
}