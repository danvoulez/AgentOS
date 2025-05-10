package logline.authz

default allow = false

allow {
    input.path == ["actions", "acionar_log_institucional"]; input.method == "POST"
    is_authenticated
    # Granular: apenas autor, admin ou manager podem confirmar/contestar fatos
    ((input.request_body.acionamento_type == "confirmar_veracidade" or input.request_body.acionamento_type == "contestar_fato") 
      and (input.claims.uid == input.extra_context.target_log_author or has_role({"admin", "manager"})))
    # "denunciar_conduta" só pode por auditor/admin/manager_level_2 e exige evidencia
    ((input.request_body.acionamento_type == "denunciar_conduta") 
      and has_role({"auditor", "admin", "manager_level_2"}) 
      and count(object.get(input.request_body, "evidencias_anexas", [])) > 0)
    # Outros acionamentos podem ter regras próprias
    reasons := []
}