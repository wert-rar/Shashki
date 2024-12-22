from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

DATABASE_URL = "postgresql://postgres:951753aA.@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Games(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    unstarted_games = Column(Integer, default=0)
    current_games = Column(Integer, default=0)
    completed_games = Column(Integer, default=0)

# Создаем таблицы в базе данных
def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
