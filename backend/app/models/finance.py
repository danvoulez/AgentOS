# agentos_core/app/models/finance.py

from pydantic import BaseModel, Field, ConfigDict  
from typing import List, Optional, Literal  
from datetime import date, datetime  
from decimal import Decimal

# --- Schemas para Respostas de Relatórios API ---

class SalesByPeriodItemAPI(BaseModel):  
    """Item de dados para o relatório de vendas."""  
    # Usar string para datas no retorno API para evitar problemas de formato/timezone  
    period_start_str: str = Field(..., alias="period_start", description="Início do período (YYYY-MM-DD ou YYYY-MM etc.)")  
    period_end_str: str = Field(..., alias="period_end", description="Fim do período (YYYY-MM-DD ou YYYY-MM etc.)")  
    # Usar string para valores monetários  
    total_revenue: str = Field(..., description="Receita total no período.")  
    total_cost: Optional[str] = Field(None, description="Custo total dos produtos vendidos (se calculado).")  
    total_margin: Optional[str] = Field(None, description="Margem total (Receita - Custo, se calculado).")  
    number_of_orders: int  
    average_order_value: str = Field(..., description="Valor médio por pedido no período.")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class SalesReportAPI(BaseModel):  
    """Estrutura da resposta do relatório de vendas."""  
    report_start_date_str: str = Field(..., alias="report_start_date", description="Data de início do relatório (YYYY-MM-DD).")  
    report_end_date_str: str = Field(..., alias="report_end_date", description="Data de fim do relatório (YYYY-MM-DD).")  
    generated_at: datetime = Field(default_factory=datetime.utcnow)  
    granularity: Literal["daily", "weekly", "monthly", "yearly", "total"]  
    filters_applied: Optional[Dict] = Field(None, description="Filtros usados para gerar o relatório (ex: channel).")  
    summary: SalesByPeriodItemAPI # Sumário total do período completo  
    details: Optional[List[SalesByPeriodItemAPI]] = None # Detalhes por sub-período

    model_config = ConfigDict(  
        populate_by_name=True,  
        from_attributes=True,  
        json_encoders={datetime: lambda v: v.isoformat()}  
    )

class CommissionReportItemAPI(BaseModel):  
    """Item para relatório de comissões."""  
    user_id: str  
    user_name: Optional[str] = None  
    period_start_str: str = Field(..., alias="period_start")  
    period_end_str: str = Field(..., alias="period_end")  
    total_sales_value_attributed: str  
    commission_rate_applied: Optional[float] = None # Ex: 0.1 para 10%  
    total_commission_earned: str  
    number_of_attributed_orders: int

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class CommissionReportAPI(BaseModel):  
    """Estrutura da resposta do relatório de comissões."""  
    report_start_date_str: str = Field(..., alias="report_start_date")  
    report_end_date_str: str = Field(..., alias="report_end_date")  
    generated_at: datetime = Field(default_factory=datetime.utcnow)  
    filters_applied: Optional[Dict] = None  
    details: List[CommissionReportItemAPI]

    model_config = ConfigDict(  
        populate_by_name=True,  
        from_attributes=True,  
        json_encoders={datetime: lambda v: v.isoformat()}  
    )

# Importar Dict para filtros  
from typing import Dict
