\# agentos_core/app/modules/finance/routers.py

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request  
from typing import Optional, Literal, List \# Adicionar List  
from datetime import date, datetime \# Adicionar datetime  
from loguru import logger

\# Dependências Auth/Roles  
from app.core.security import CurrentUser, UserInDB, require_role

\# Modelos API de Relatório  
from app.models.finance import SalesReportAPI, CommissionReportAPI \# Usar sufixo API

\# Serviço e Repositórios necessários  
from .services import FinanceService, get_finance_service  
from app.modules.sales.repository import OrderRepository, get_order_repository  
from app.modules.banking.repository import TransactionRepository, get_transaction_repository \# Para comissões  
from app.modules.people.repository import UserRepository, get_user_repository \# Para comissões

\# Auditoria (Opcional para endpoints de leitura)  
from app.modules.office.services_audit import AuditService, get_audit_service

finance_router \= APIRouter()

@finance_router.get(  
    \\"/reports/sales\\",  
    response_model=SalesReportAPI, \# Retorna modelo API  
    \# Quem pode ver relatórios financeiros?  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"finance\\", \\"sales_manager\\"\]))\],  
    summary=\\"Generate Aggregated Sales Report\\",  
    tags=\[\\"Finance & Reports\\"\]  
)  
async def get_sales_report_endpoint(  
    request: Request, \# Para auditoria  
    start_date: date \= Query(..., description=\\"Start date (YYYY-MM-DD)\\"),  
    end_date: date \= Query(..., description=\\"End date (YYYY-MM-DD)\\"),  
    granularity: Literal\[\\"daily\\", \\"weekly\\", \\"monthly\\", \\"yearly\\", \\"total\\"\] \= Query(\\"total\\", description=\\"Aggregation level\\"),  
    channel: Optional\[str\] \= Query(None, description=\\"Filter by sales channel\\"),  
    \# Adicionar outros filtros se necessário  
    finance_service: FinanceService \= Depends(get_finance_service),  
    order_repo: OrderRepository \= Depends(get_order_repository),  
    audit_service: AuditService \= Depends(get_audit_service), \# Opcional  
    current_user: UserInDB \= Depends(get_current_active_user) \# Para auditoria  
):  
    \\"\\"\\"Generates an aggregated sales report based on confirmed/completed orders.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    log.info(f\\"Endpoint: Gerando relatório de vendas ({start_date} a {end_date}, Gran: {granularity})\\")

    if start_date \> end_date:  
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=\\"Start date cannot be after end date.\\")

    try:  
        \# Service faz a agregação e retorna modelo interno SalesReport  
        report_internal \= await finance_service.generate_sales_report(  
            order_repo=order_repo,  
            start_date=start_date,  
            end_date=end_date,  
            granularity=granularity,  
            channel=channel,  
        )  
        \# Converter modelo interno para modelo API (principalmente datas/decimals para string)  
        report_api \= SalesReportAPI.model_validate(report_internal)

        \# Logar auditoria (opcional, mas útil)  
        await audit_service.log_audit_event(  
            action=\\"finance_report_generated\\", status=\\"success\\", entity_type=\\"SalesReport\\",  
            request=request, current_user=current_user,  
            details={\\"report_type\\": \\"sales\\", \\"start\\": str(start_date), \\"end\\": str(end_date), \\"granularity\\": granularity}  
        )  
        return report_api

    except ValueError as ve: \# Erro de validação do service (ex: granularidade)  
         log.warning(f\\"Erro de validação ao gerar relatório de vendas: {ve}\\")  
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))  
    except RuntimeError as re: \# Erro de agregação DB do service  
         log.error(f\\"Erro de runtime ao gerar relatório de vendas: {re}\\")  
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(re))  
    except Exception as e:  
         log.exception(\\"Erro inesperado ao gerar relatório de vendas.\\")  
         \# Logar auditoria de falha?  
         await audit_service.log_audit_event(action=\\"finance_report_failed\\", status=\\"failure\\", ...)  
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=\\"An unexpected error occurred.\\")

@finance_router.get(  
    \\"/reports/commissions\\",  
    response_model=CommissionReportAPI, \# Usar modelo API  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"finance\\"\]))\],  
    summary=\\"Generate Commissions Report (Basic)\\",  
    tags=\[\\"Finance & Reports\\"\]  
)  
async def get_commission_report_endpoint(  
    request: Request,  
    start_date: date \= Query(..., description=\\"Start date (YYYY-MM-DD)\\"),  
    end_date: date \= Query(..., description=\\"End date (YYYY-MM-DD)\\"),  
    sales_rep_id: Optional\[str\] \= Query(None, description=\\"Filter by specific Sales Rep User ID\\"),  
    \# Adicionar outros filtros se necessário  
    finance_service: FinanceService \= Depends(get_finance_service),  
    order_repo: OrderRepository \= Depends(get_order_repository),  
    user_repo: UserRepository \= Depends(get_user_repository), \# Para buscar nomes  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"Generates a basic commissions report based on completed orders and a default rate.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    log.info(f\\"Endpoint: Gerando relatório de comissões ({start_date} a {end_date})\\")

    if start_date \> end_date: raise HTTPException(400, \\"Start date cannot be after end date.\\")

    try:  
        \# Chamar service para gerar o relatório (precisa ser implementado)  
        report_internal \= await finance_service.generate_commission_report(  
             order_repo=order_repo,  
             user_repo=user_repo,  
             start_date=start_date,  
             end_date=end_date,  
             sales_rep_id_str=sales_rep_id  
        )  
        \# Converter para modelo API  
        report_api \= CommissionReportAPI.model_validate(report_internal)

        await audit_service.log_audit_event(action=\\"finance_report_generated\\", status=\\"success\\", entity_type=\\"CommissionReport\\",...)  
        return report_api  
    except NotImplementedError: \# Capturar se o service ainda não implementou  
         raise HTTPException(status_code=501, detail=\\"Commission report functionality is not yet fully implemented.\\")  
    except Exception as e:  
        log.exception(\\"Erro ao gerar relatório de comissões.\\")  
        await audit_service.log_audit_event(action=\\"finance_report_failed\\", status=\\"failure\\", entity_type=\\"CommissionReport\\", ...)  
        raise HTTPException(status_code=500, detail=\\"Error generating commission report.\\")
