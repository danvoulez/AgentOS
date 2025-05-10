import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import (
    LogEvent, GatewayRequest, LLMInterpretationResponse, LLMFormSchema,
    RegistrarVendaData, RelatoQuebraData, LogAcionadoInstitucionalmenteData,
)

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "docs" / "schemas"
(SCHEMAS_DIR / "data_schemas").mkdir(parents=True, exist_ok=True)

def export_schema(model, filename):
    schema = model.model_json_schema()
    with open(SCHEMAS_DIR / filename, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"Exported {filename}")

if __name__ == "__main__":
    export_schema(LogEvent, "LogEvent.json")
    export_schema(GatewayRequest, "GatewayRequest.json")
    export_schema(LLMInterpretationResponse, "LLMInterpretationResponse.json")
    export_schema(LLMFormSchema, "LLMFormSchema.json")
    export_schema(RegistrarVendaData, "data_schemas/RegistrarVendaData.json")
    export_schema(RelatoQuebraData, "data_schemas/RelatoQuebraData.json")
    export_schema(LogAcionadoInstitucionalmenteData, "data_schemas/LogAcionadoInstitucionalmenteData.json")
    print(f"All schemas exported to: {SCHEMAS_DIR}")