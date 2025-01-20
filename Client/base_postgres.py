from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, validates
from sqlalchemy import create_engine

Base = declarative_base()

#DATABASE_URL = "postgresql://postgres:951753aA.@localhost:5432/postgres"
DATABASE_URL = "postgresql://cloud_user:sqfxuf1Ko&kh@kluysopgednem.beget.app:5432/default_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Game(Base):
    __tablename__ = "games"

    game_id = Column(Integer, primary_key=True, index=True)
    f_user = Column(String, nullable=True)
    c_user = Column(String, nullable=True)
    status = Column(String, default="unstarted")

    moves = relationship("GameMove", back_populates="game")

class GameMove(Base):
    __tablename__ = "game_moves"

    move_id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey('games.game_id'))
    player = Column(String, nullable=False)
    from_x = Column(Integer, nullable=False)
    from_y = Column(Integer, nullable=False)
    to_x = Column(Integer, nullable=False)
    to_y = Column(Integer, nullable=False)
    move_time = Column(DateTime, default=func.now())
    captured_piece = Column(Boolean, default=False)
    promotion = Column(Boolean, default=False)

    game = relationship("Game", back_populates="moves")

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
