"""Genera documentos desde el esquema SQL, modelos y contrato OpenAPI."""
import ast
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.main import app  # noqa: E402

NOTES = {
    "hourly_rate": "Precio por hora en céntimos de sol.",
    "total": "Importe total en céntimos de sol, calculado por el backend.",
    "starts": "Inicio, en minutos desde 00:00, hora de Perú.",
    "ends": "Fin exclusivo, en minutos desde 00:00, hora de Perú.",
    "opens": "Apertura en minutos desde 00:00.",
    "closes": "Cierre en minutos desde 00:00.",
    "weekday": "0=Lunes, 6=Domingo.",
    "access_hash": "SHA-256 de una clave aleatoria de acceso de 256 bits.",
    "date": "Fecha local del evento, ISO YYYY-MM-DD.",
    "created_at": "Marca de creación UTC generada por SQLite.",
    "status": "Pendiente, Confirmada o Cancelada.",
    "payment": "Pendiente o Pagado; registro manual por la sede.",
}
TABLE_METADATA = {
    "courts": ("PRAGMA foreign_key_list(courts)", "PRAGMA table_info(courts)"),
    "users": ("PRAGMA foreign_key_list(users)", "PRAGMA table_info(users)"),
    "schedules": ("PRAGMA foreign_key_list(schedules)", "PRAGMA table_info(schedules)"),
    "rentals": ("PRAGMA foreign_key_list(rentals)", "PRAGMA table_info(rentals)"),
}


def generate():
    output = ROOT / "docs" / "generated"
    output.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(":memory:")
    db.executescript((ROOT / "app" / "schema.sql").read_text(encoding="utf-8"))
    tables = [row[0] for row in db.execute(
        "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    dictionary = ["# Diccionario de datos", "", "Fuente: app/schema.sql. Motor: SQLite.", ""]
    er = ["erDiagram"]
    for table in tables:
        dictionary += [f"## {table}", "", "| Campo | Tipo | Obligatorio | Clave | Descripción |",
                       "|---|---|---|---|---|"]
        fk_query, columns_query = TABLE_METADATA[table]
        foreign = {row[3]: row[2] + "." + row[4] for row in db.execute(fk_query)}
        er.append(f"  {table} {{")
        for _, name, kind, notnull, default, pk in db.execute(columns_query):
            key = "PK" if pk else ("FK → " + foreign[name] if name in foreign else "")
            description = NOTES.get(name, "Identificador único." if pk else name.replace("_", " ").capitalize())
            if default is not None:
                description += " Predeterminado: " + str(default) + "."
            dictionary.append(f"| {name} | {kind} | {'Sí' if notnull or pk else 'No'} | {key} | {description} |")
            er.append(f"    {kind.lower()} {name}" + (" PK" if pk else " FK" if name in foreign else ""))
        er.append("  }")
        dictionary.append("")
    er += ["  courts ||--o{ schedules : dispone", "  courts ||--o{ rentals : recibe",
           "  users ||--o{ rentals : solicita"]
    db.close()
    classes = ["classDiagram"]
    tree = ast.parse((ROOT / "app" / "models.py").read_text(encoding="utf-8"))
    for item in tree.body:
        if not isinstance(item, ast.ClassDef):
            continue
        classes.append("  class " + item.name + " {")
        for field in item.body:
            if isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name):
                annotation = ast.unparse(field.annotation)
                kind = "string" if annotation.startswith("Literal") else annotation
                classes.append("    +" + kind + " " + field.target.id)
        classes.append("  }")
        for base in item.bases:
            if isinstance(base, ast.Name) and base.id == "InputModel":
                classes.append("  InputModel <|-- " + item.name)
    components = [
        "flowchart TD", '  UI["Frontend HTML / CSS / JavaScript"]',
        '  API["API REST FastAPI"]', '  AUTH["Validación y controles de acceso"]',
        '  DB["Repositorio SQLite"]', '  SQL["Esquema relacional"]',
        "  UI --> API", "  API --> AUTH", "  API --> DB", "  DB --> SQL",
    ]
    deployment = [
        "flowchart TD", '  U["Navegador"]', '  GH["GitHub Actions"]',
        '  Q["Pruebas, Sonar, Snyk y Semgrep"]', '  ACR["Azure Container Registry"]',
        '  WEB["Azure App Service Linux: 1 instancia"]', '  HOME["SQLite en /home/data persistente"]',
        '  STATE["Azure Storage: estado Terraform"]',
        "  U -->|HTTPS| WEB", "  GH --> Q", "  Q -->|Imagen aprobada| ACR",
        "  ACR -->|Identidad administrada| WEB", "  WEB --> HOME", "  GH -->|Terraform| STATE",
        "  GH -->|Provisiona y despliega| WEB",
    ]
    diagrams = {"entidad-relacion": er, "clases": classes, "componentes": components, "despliegue": deployment}
    (output / "diccionario-datos.md").write_text("\n".join(dictionary).rstrip() + "\n", encoding="utf-8")
    compiled = ["# Diagramas de la aplicación", "", "Generados con scripts/generate_docs.py.", ""]
    for name, lines in diagrams.items():
        mermaid = "\n".join(lines) + "\n"
        (output / (name + ".mmd")).write_text(mermaid, encoding="utf-8")
        compiled += ["## " + name.replace("-", " ").capitalize(), "", "```mermaid", mermaid.rstrip(), "```", ""]
    (output / "diagramas.md").write_text("\n".join(compiled), encoding="utf-8")
    contract = app.openapi()
    (output / "openapi.json").write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Documentación generada en docs/generated.")


if __name__ == "__main__":
    generate()
