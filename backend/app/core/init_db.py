"""Dev иницијализација: ја вклучува pgvector екстензијата и ги креира табелите.

За продукција/понатамошен развој користи Alembic миграции.
Стартување:  python -m app.core.init_db
"""
from sqlalchemy import text

from app.core.database import Base, engine
from app.models import listing, agent_log  # noqa: F401  (регистрација на моделите)


def init() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    print("✔ Базата е иницијализирана (табели + pgvector).")


if __name__ == "__main__":
    init()
