"""
Script de migración: elimina la BD antigua y la regenera con el nuevo schema.
Ejecutar: python -m src.database.migrate
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import init_db, seed_demo_data


def migrate():
    db_path = Path("dental_clinic.db")
    if db_path.exists():
        os.remove(db_path)
        print(f"✓ Base de datos anterior eliminada: {db_path}")

    init_db()
    print("✓ Tablas creadas con el nuevo schema")

    seed_demo_data()
    print("✓ Datos de demostración insertados")
    print("\n¡Migración completada exitosamente!")


if __name__ == "__main__":
    migrate()
