\# agentos_core/app/modules/banking/routers.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request  
from typing import List, Optional  
from datetime import datetime  
from loguru import logger

\# Dependências Auth/Roles  
from app.core.security import CurrentUser, UserInDB, require_role

\# Modelos API  
from app.models.banking import TransactionAPI, TransactionCreateAPI, TransactionUpdateAPI

\# Modelos Internos/DB  
from .models import TransactionCreateInternal, TransactionUpdateInternal, TRANSACTION_STATUSES \# Para validação

\# Repositórios e Serviços  
from .repository import TransactionRepository, get_transaction_repository  
from .services import BankingService, get_banking_service  
from app.core.counters import CounterService, get_counter_service \# Para criar  
from app.modules.office.services_audit import AuditService, get_audit_service \# Para auditoria

banking_router \= APIRouter()

@banking_router.post(  
    \\"/\\",  
    response_model=TransactionAPI, \# Retorna modelo API  
    status_code=status.HTTP_201_CREATED,  
    \# Quem pode registrar transações manualmente? Admin, Finance, Sistema?  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"finance\\", \\"system\\"\]))\],  
    summary=\\"Record a financial transaction\\",  
    tags=\[\\"Banking\\"\]  
)  
async def record_transaction_endpoint(  
    request: Request,  
    transaction_in: TransactionCreateAPI, \# Recebe modelo API  
    banking_service: BankingService \= Depends(get_banking_service),  
    banking_repo: TransactionRepository \= Depends(get_transaction_repository),  
    counter_service: CounterService \= Depends(get_counter_service),  
    audit_service: AuditService \= Depends(get_audit_service),  
    \# Usuário logado ou sistema? Se sistema, como autenticar? Usar API Key?  
    \# Por enquanto, assumir usuário logado com role apropriada.  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"(Admin/System Only) Records a new financial transaction.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    log.info(f\\"Endpoint: Registrando nova transação tipo '{transaction_in.type}'...\\")  
    try:  
        \# Converter API model para Internal model (principalmente amount str \-\> Decimal)  
        \# Service deve fazer essa validação/conversão? Ou fazemos aqui? Fazer no service.  
        \# Chamada direta ao service, que lida com ref, validação, criação, auditoria.  
        \# O service precisa do audit_repo e current_user para logar.  
        created_transaction \= await banking_service.record_transaction(  
            transaction_in=transaction_in, \# Passar modelo API  
            banking_repo=banking_repo,  
            counter_service=counter_service,  
            audit_service=audit_service,  
            current_user=current_user  
        )  
        \# Converter modelo DB de volta para API (se necessário, service pode fazer isso)  
        return TransactionAPI.model_validate(created_transaction)

    except HTTPException as http_exc: \# Capturar 4xx do service  
        log.warning(f\\"Falha ao registrar transação: {http_exc.detail}\\")  
        \# Auditoria deve ter sido logada no service  
        raise http_exc  
    except (ValueError, RuntimeError) as e: \# Capturar erros internos do service/repo  
        log.error(f\\"Erro interno ao registrar transação: {e}\\")  
        \# Auditoria deve ter sido logada no service  
        raise HTTPException(status_code=500, detail=str(e))  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao registrar transação: {e}\\")  
        await audit_service.log_audit_event(action=\\"transaction_record_failed\\", status=\\"failure\\", ...) \# Logar falha genérica  
        raise HTTPException(status_code=500, detail=\\"Internal server error recording transaction.\\")

@banking_router.get(  
    \\"/\\",  
    response_model=List\[TransactionAPI\],  
    \# Quem pode listar?  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"finance\\", \\"support\\"\]))\],  
    summary=\\"List financial transactions\\",  
    tags=\[\\"Banking\\"\]  
)  
async def list_transactions_endpoint(  
    request: Request, \# Para auditoria (opcional)  
    start_date: Optional\[datetime\] \= Query(None, description=\\"Filter by start date/time (ISO format)\\"),  
    end_date: Optional\[datetime\] \= Query(None, description=\\"Filter by end date/time (ISO format)\\"),  
    transaction_type: Optional\[str\] \= Query(None, description=\\"Filter by transaction type\\"),  
    status: Optional\[str\] \= Query(None, description=\\"Filter by transaction status\\"),  
    order_id: Optional\[str\] \= Query(None, description=\\"Filter by associated order ID\\"),  
    user_id: Optional\[str\] \= Query(None, description=\\"Filter by associated user ID\\"), \# Adicionado filtro user  
    skip: int \= Query(0, ge=0),  
    limit: int \= Query(100, ge=1, le=500),  
    banking_service: BankingService \= Depends(get_banking_service),  
    banking_repo: TransactionRepository \= Depends(get_transaction_repository),  
    audit_service: AuditService \= Depends(get_audit_service), \# Opcional  
    current_user: UserInDB \= Depends(get_current_active_user) \# Para auditoria  
):  
    \\"\\"\\"Lists financial transactions with filters for reporting and auditing.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Listando transações...\\")  
    \# Validar tipos de filtro (Transaction Types/Statuses)  
    if transaction_type and transaction_type not in TRANSACTION_TYPES.__args__:  
        raise HTTPException(400, \\"Invalid transaction_type filter\\")  
    if status and status not in TRANSACTION_STATUSES.__args__:  
        raise HTTPException(400, \\"Invalid status filter\\")

    transactions \= await banking_service.list_transactions(  
        banking_repo=banking_repo, start_date=start_date, end_date=end_date,  
        transaction_type=transaction_type, status=status, order_id=order_id, user_id=user_id,  
        skip=skip, limit=limit  
    )  
    \# Logar auditoria (opcional)  
    \# await audit_service.log_audit_event(action=\\"transactions_listed\\", ...)  
    \# Service retorna lista de modelos DB, router converte para API  
    return \[TransactionAPI.model_validate(t) for t in transactions\]

@banking_router.get(  
    \\"/{transaction_id}\\",  
    response_model=TransactionAPI,  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"finance\\", \\"support\\"\]))\],  
    summary=\\"Get transaction details by ID\\",  
    tags=\[\\"Banking\\"\]  
)  
async def get_transaction_endpoint(  
    request: Request,  
    transaction_id: str \= Path(..., description=\\"ID da Transação (ObjectId)\\"),  
    banking_service: BankingService \= Depends(get_banking_service),  
    banking_repo: TransactionRepository \= Depends(get_transaction_repository),  
    audit_service: AuditService \= Depends(get_audit_service), \# Opcional  
    current_user: UserInDB \= Depends(get_current_active_user) \# Para auditoria  
):  
    \\"\\"\\"Retrieves details for a specific financial transaction.\\"\\"\\"  
    log \= logger.bind(transaction_id=transaction_id, user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Buscando transação por ID...\\")  
    transaction \= await banking_service.get_transaction(transaction_id, banking_repo)  
    if not transaction:  
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=\\"Transaction not found\\")  
    \# Logar view (opcional)  
    \# await audit_service.log_audit_event(action=\\"transaction_viewed\\", ...)  
    return TransactionAPI.model_validate(transaction)

@banking_router.patch(  
    \\"/{transaction_id}/status\\",  
    response_model=TransactionAPI,  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"finance\\"\]))\], \# Quem pode mudar status?  
    summary=\\"Update transaction status\\",  
    tags=\[\\"Banking\\"\]  
)  
async def update_transaction_status_endpoint(  
    request: Request,  
    transaction_id: str \= Path(..., description=\\"ID da Transação a ser atualizada\\"),  
    payload: TransactionUpdateAPI, \# Recebe modelo API (só com status/desc)  
    banking_service: BankingService \= Depends(get_banking_service),  
    banking_repo: TransactionRepository \= Depends(get_transaction_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"Updates the status (and optionally description) of a transaction.\\"\\"\\"  
    log \= logger.bind(transaction_id=transaction_id, user_id=str(current_user.id))  
    log.info(f\\"Endpoint: Atualizando status da transação para '{payload.status}'...\\")

    if not payload.status: \# Garantir que o status veio no payload PATCH  
        raise HTTPException(status_code=400, detail=\\"New status is required in payload.\\")  
    \# Validar se o status é permitido (modelo Pydantic já faz isso se usar Literal)  
    \# if payload.status not in TRANSACTION_STATUSES.__args__: ...

    try:  
        \# Chamar service que valida, atualiza e audita  
        updated_transaction \= await banking_service.update_transaction_status(  
            transaction_id_str=transaction_id,  
            new_status=payload.status,  
            banking_repo=banking_repo,  
            audit_service=audit_service,  
            current_user=current_user  
        )  
        if not updated_transaction:  
            \# Service não encontrou ou falhou em atualizar  
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=\\"Transaction not found or update failed.\\")

        return TransactionAPI.model_validate(updated_transaction)

    except HTTPException as http_exc:  
        \# Falha de validação ou erro interno do service  
        raise http_exc  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao atualizar status da transação {transaction_id}\\")  
        \# Logar auditoria de falha aqui? Service já deve ter logado.  
        raise HTTPException(status_code=500, detail=\\"Internal server error updating transaction status.\\")
