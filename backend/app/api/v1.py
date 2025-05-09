# agentos_core/app/api/v1.py

from fastapi import APIRouter

# Importar routers de cada módulo/endpoint  
from app.modules.people.routers import auth_router, users_router # Auth e Users de People  
from app.modules.sales.routers import products_router, orders_router # Produtos e Pedidos de Sales  
from app.modules.delivery.routers import delivery_router # Entregas  
from app.modules.agreements.routers import agreement_router # Acordos  
from app.modules.tasks.routers import tasks_router # Tarefas  
from app.modules.banking.routers import banking_router # Banking/Transações  
from app.modules.finance.routers import finance_router # Relatórios Financeiros  
from app.modules.office.routers import office_router # Settings e Audit Logs  
from app.modules.stock.routers import stock_router # Itens de Estoque/RFID  
from app.modules.advisor.routers import advisor_router # Histórico do Advisor  
from app.modules.gateway.routers import gateway_router # Processamento LLM Principal

# Importar routers de endpoints core (se houver)  
from app.api.endpoints import status # Status endpoint

# Router principal da V1  
# Pode adicionar dependências globais para V1 aqui se necessário  
# ex: dependencies=[Depends(verify_api_key_or_jwt)]  
api_v1_router = APIRouter()

# Incluir os routers específicos com seus prefixos e tags  
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])  
api_v1_router.include_router(users_router, prefix="/users", tags=["Users & People"]) # Juntar People?  
api_v1_router.include_router(products_router, prefix="/products", tags=["Sales - Products"])  
api_v1_router.include_router(orders_router, prefix="/orders", tags=["Sales - Orders"])  
api_v1_router.include_router(stock_router, prefix="/stock", tags=["Stock & RFID"]) # Adicionar Stock  
api_v1_router.include_router(delivery_router, prefix="/deliveries", tags=["Delivery"])  
api_v1_router.include_router(agreements_router, prefix="/agreements", tags=["Agreements"])  
api_v1_router.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])  
api_v1_router.include_router(banking_router, prefix="/banking", tags=["Banking"])  
api_v1_router.include_router(finance_router, prefix="/finance", tags=["Finance & Reports"])  
api_v1_router.include_router(office_router, prefix="/office", tags=["Office & Admin"])  
api_v1_router.include_router(advisor_router, prefix="/advisor", tags=["AI Advisor"]) # Adicionar Advisor  
api_v1_router.include_router(gateway_router, prefix="/gateway", tags=["LLM Gateway"])

# Endpoints "core" como status podem ficar aqui ou em endpoints separados  
api_v1_router.include_router(status.router, prefix="/status", tags=["Status"])

# Rota raiz da V1  
@api_v1_router.get("/", tags=["API Root"], summary="Get V1 API Root")  
async def read_v1_root():  
    """Provides a welcome message for the V1 API."""  
    return {"message": "Welcome to AgentOS Core API v1"}
