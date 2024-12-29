from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

<<<<<<< HEAD
#DATABASE_URL = "postgresql://postgres:951753aA.@localhost:5432/postgres"
DATABASE_URL = "postgresql://cloud_user:sqfxuf1Ko&kh@kluysopgednem.beget.app:5432/default_db"
=======
DATABASE_URL = "postgresql://postgres:951753aA.@localhost:5432/postgres"
#DATABASE_URL = "postgresql://cloud_user:sqfxuf1Ko&kh@kluysopgednem.beget.app:5432/default_db"
>>>>>>> ad8c652e404324df3c7139a97df6933eb9442e67

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Game(Base):
    __tablename__ = "games"

    game_id = Column(Integer, primary_key=True, index=True)
    f_user = Column(String, nullable=True)
    c_user = Column(String, nullable=True)
    status = Column(String, default="unstarted")

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()