import asyncio
import httpx
from app.config import settings

async def seed():
    admin_token = "ADMIN_TOKEN_HERE" # Substitua por token real ou gere via devtools
    headers = {"Authorization": f"Bearer {admin_token}"}
    api = f"http://localhost:{settings.API_PORT_FOR_TESTS or 8001}{settings.API_V1_STR}"
    async with httpx.AsyncClient() as client:
        # 1. Criar venda
        venda_payload = {
            "customer_id": "seed_customer",
            "items": [{"product_id": "prod_seed", "quantity": 2, "price_per_unit_str": "9.99", "name": "Seed Product"}],
            "channel": "seed_script",
            "notes": "Venda seed",
            "client_order_ref": "seed_order_001"
        }
        resp = await client.post(f"{api}/actions/registrar_venda", json=venda_payload, headers=headers)
        print("RegistrarVenda:", resp.status_code, resp.json())
        # 2. Entrada estoque
        estoque_payload = {
            "item_id": "prod_seed",
            "qty": 10,
            "reason": "Seed estoque",
            "channel": "seed_script"
        }
        resp = await client.post(f"{api}/actions/entrada_estoque", json=estoque_payload, headers=headers)
        print("EntradaEstoque:", resp.status_code, resp.json())
        # 3. Criar despacho
        despacho_payload = {
            "despacho_type": "validar_prelog_whatsapp",
            "assigned_to": "seed_staff",
            "summary_of_context": "Despacho seed",
            "notes": ["Criado via seed_db.py"]
        }
        resp = await client.post(f"{api}/actions/create_despacho", json=despacho_payload, headers=headers)
        print("Despacho:", resp.status_code, resp.json())

if __name__ == "__main__":
    asyncio.run(seed())