from datetime import datetime
from sqlalchemy import select, update, and_, or_, union_all, func, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
import logging
from thecheckers import utils
from thecheckers.models import Base, Player, CompletedGames, RememberToken, FriendRelation, GameInvitation, Game, Room

DATABASE_URL = "postgresql://postgres:951753aA.@localhost:5432/postgres"
#DATABASE_URL = "postgresql://J0muty:951753aA.!@ogustidid.beget.app:5432/Beget"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def connect(method):
    """
            A decorator function that establishes a connection to the database and manages the session.
            It wraps the provided method and ensures that the database session is properly initialized, committed, and closed.

            Parameters:
            method (callable): The function to be decorated. This function should accept a database session as a keyword argument.

            Returns:
            wrapper (callable): The decorated function. This function will handle the database session management.
    """
    def wrapper(*args, **kwargs):
        with SessionLocal() as session:
            try:
                return method(*args, session=session)
            except Exception as e:
                session.rollback()
                raise Exception(f'Ошибка при работе с базой данных: {repr(e)} args:\n{args} kwargs:\n{kwargs}')
            finally:
                session.close()
    return wrapper

def init_db():
    Base.metadata.create_all(bind=engine)

# ----------------------------------------------------------------------------------------------------------------------

@connect
def check_user_exists(user_login, session: Session | None = None):
    return session.scalar(select(Player).where(Player.login == user_login)) is not None

@connect
def register_user(user_login, user_password, session: Session | None = None):
    hashed_password = utils.hash_password(user_password)
    try:
        with session.begin():
            session.add(Player(login=user_login, password=hashed_password))
        return True
    except IntegrityError:
        logging.warning(f"Пользователь с логином '{user_login}' уже существует.")
        return False

@connect
def authenticate_user(user_login, user_password, session: Session | None = None):
    row = session.scalar(select(Player).where(Player.login == user_login))
    if row:
        stored_password = row.password
        if utils.verify_password(user_password, stored_password):
            logging.info(f"Пользователь '{user_login}' успешно аутентифицирован.")
            return True
        else:
            logging.warning(f"Неверный пароль для пользователя '{user_login}'.")
            return False
    else:
        logging.warning(f"Пользователь '{user_login}' не найден.")
        return False

@connect
def get_user_by_login(user_login, session: Session | None = None) -> dict:
    user = session.scalar(select(Player).where(Player.login == user_login))
    return user.to_dict() if user else None

@connect
def update_user_rang(user_login, points, session: Session | None = None):
    try:
        with session.begin():
            session.execute(update(Player).where(Player.login == user_login).values(rang=func.coalesce(Player.rang, 0) + points))
    except Exception as e:
        logging.error(f"Ошибка обновления ранга: {e}")

@connect
def update_user_stats(user_login, wins=0, losses=0, draws=0, session: Session | None = None):
    try:
        with session.begin():
            session.execute(update(Player).where(Player.login == user_login).values(wins=Player.wins + wins, losses=Player.losses + losses, draws=Player.draws + draws))
    except Exception as e:
        logging.error(f"Ошибка обновления статистики: {e}")

@connect
def add_completed_game(user_login, game_id, date_start, rating_before, rating_after, rating_change, result, session: Session | None = None):
    try:
        with session.begin():
            session.add(CompletedGames(user_login=user_login, game_id=game_id, date_start=date_start, rating_before=rating_before, rating_after=rating_after, rating_change=rating_change, result=result))
    except Exception as e:
        logging.error(f"Ошибка при добавлении завершенной игры: {e}")

@connect
def get_user_history(user_login, session: Session | None = None):
    games = session.scalars(select(CompletedGames).where(CompletedGames.user_login == user_login).order_by(CompletedGames.ID.asc())).all()
    return [game.to_dict() for game in games]

@connect
def update_user_avatar(user_login, filename, session: Session | None = None):
    session.execute(update(Player).where(Player.login == user_login).values(avatar_filename=filename))
    session.commit()

@connect
def add_remember_token(user_login, token, expires_at, session: Session | None = None):
    try:
        session.add(RememberToken(user_login=user_login, token=token, expires_at=expires_at.isoformat()))
        logging.info(f"Токен для пользователя '{user_login}' добавлен.")
        return True
    except Exception as e:
        logging.error(f"Ошибка при добавлении токена: {e}")
        return False

@connect
def get_user_by_remember_token(token, session: Session | None = None):
    row = session.scalar(select(RememberToken).where(RememberToken.token == token))
    if row:
        expires_at = datetime.fromisoformat(row.expires_at)
        if datetime.now() < expires_at:
            return row.user_login
        else:
            delete_remember_token(token, session)
            return None
    return None

@connect
def delete_remember_token(token, session: Session | None = None):
    try:
        r = session.scalar(select(RememberToken).where(RememberToken.token == token))
        session.delete(r)
        session.commit()
        logging.info(f"Токен '{token}' удален.")
    except Exception as e:
        logging.error(f"Ошибка при удалении токена: {e}")

@connect
def delete_all_remember_tokens(user_login, session: Session | None = None):
    try:
        r = session.scalars(select(RememberToken).where(RememberToken.user_login == user_login))
        for token in r:
            session.delete(token)
        session.commit()
        logging.info(f"Все токены для пользователя '{user_login}' удалены.")
    except Exception as e:
        logging.error(f"Ошибка при удалении токенов: {e}")

@connect
def search_users(query: str, exclude_user: str = None, limit: int = 10, session: Session | None = None):
    if not query:
        return []
    try:
        like_query = f"{query}%"
        if exclude_user:
            stmt = select(Player.login).where(and_(Player.login.like(like_query), Player.login != exclude_user)).limit(limit)
        else:
            stmt = select(Player.login).where(Player.login.like(like_query)).limit(limit)
        rows = session.scalars(stmt)
        return [row for row in rows]
    except Exception as e:
        logging.error(f"Ошибка при поиске пользователей: {e}")
        return []

@connect
def get_top_players(limit: int = 3, session: Session | None = None):
    try:
        players = session.scalars(select(Player).order_by(Player.rang.desc()).limit(limit)).all()
        return [player.to_dict() for player in players]
    except Exception as e:
        logging.error(f"Ошибка при получении топ игроков: {e}")
        return []

# ----------------------------------------------------------------------------------------------------------------------

@connect
def send_game_invite_db(sender: str, receiver: str, game_id: int, session: Session | None = None) -> str:
    if sender == receiver:
        return "self_invite"
    existing = session.query(GameInvitation).filter_by(from_user=sender, to_user=receiver, game_id=game_id).first()
    if existing:
        if existing.status == "pending":
            return "already_sent"
        elif existing.status == "declined":
            existing.status = "pending"
            session.commit()
            return "sent_again"
    reverse_existing = session.query(GameInvitation).filter_by(from_user=receiver, to_user=sender, game_id=game_id).first()
    if reverse_existing and reverse_existing.status == "pending":
        return "reverse_already_sent"
    new_invite = GameInvitation(from_user=sender, to_user=receiver, status="pending", game_id=game_id)
    session.add(new_invite)
    session.commit()
    return "sent"

@connect
def respond_game_invite_db(from_user: str, to_user: str, game_id: int, response: str, session: Session | None = None) -> bool:
    invite = session.query(GameInvitation).filter_by(from_user=from_user, to_user=to_user, game_id=game_id, status="pending").first()
    if not invite:
        return False
    if response == "accept":
        invite.status = "accepted"
    else:
        invite.status = "declined"
    session.commit()
    if invite.status == "accepted":
        db_game = session.query(Game).filter_by(game_id=game_id).first()
        if db_game and db_game.c_user is None:
            db_game.c_user = to_user
            session.commit()
    return True

@connect
def remove_game_invite_by_game_id(game_id: int, session: Session | None = None):
    invites = session.query(GameInvitation).filter_by(game_id=game_id).all()
    for inv in invites:
        session.delete(inv)
    session.commit()

@connect
def send_friend_request_db(sender: str, receiver: str, session: Session | None = None) -> str:
    if sender == receiver:
        return "self_request"
    try:
        with session.begin():
            existing = session.query(FriendRelation).filter_by(user_login=sender, friend_login=receiver).first()
            if existing:
                if existing.status == "pending":
                    return "already_sent"
                elif existing.status == "accepted":
                    return "already_friends"
                elif existing.status == "declined":
                    existing.status = "pending"
                    return "sent_again"
                else:
                    return "error"
            reverse_existing = session.query(FriendRelation).filter_by(user_login=receiver, friend_login=sender).first()
            if reverse_existing:
                if reverse_existing.status == "pending":
                    return "receiver_already_sent"
                elif reverse_existing.status == "accepted":
                    return "already_friends"
                elif reverse_existing.status == "declined":
                    reverse_existing.status = "pending"
                    return "sent_again"
                else:
                    return "error"
            new_request = FriendRelation(user_login=sender, friend_login=receiver, status="pending")
            session.add(new_request)
        return "sent"
    except Exception as e:
        logging.error(f"Ошибка при отправке запроса в друзья: {e}")
        return "error"

@connect
def get_incoming_friend_requests_db(user: str, session: Session | None = None) -> list:
    records = session.query(FriendRelation).filter_by(friend_login=user, status="pending").all()
    return [r.user_login for r in records]

@connect
def respond_friend_request_db(sender: str, receiver: str, response: str, session: Session | None = None) -> bool:
    record = session.query(FriendRelation).filter_by(user_login=sender, friend_login=receiver, status="pending").first()
    if not record:
        return False
    if response == "accept":
        record.status = "accepted"
    elif response == "decline":
        record.status = "declined"
    else:
        return False
    session.commit()
    return True

@connect
def get_friends_db(user: str, session: Session | None = None) -> list:
    sent_query = select(FriendRelation.friend_login).where(FriendRelation.user_login == user, FriendRelation.status == "accepted")
    received_query = select(FriendRelation.user_login).where(FriendRelation.friend_login == user, FriendRelation.status == "accepted")
    union_query = union_all(sent_query, received_query)
    friends = session.scalars(union_query).all()
    return list(set(friends))

@connect
def remove_friend_db(user: str, friend_username: str, session: Session | None = None) -> bool:
    try:
        with session.begin():
            relations = session.query(FriendRelation).filter(or_(and_((FriendRelation.user_login == user), (FriendRelation.friend_login == friend_username)), and_((FriendRelation.user_login == friend_username), (FriendRelation.friend_login == user)))).all()
            if not relations:
                return False
            for rel in relations:
                session.delete(rel)
        return True
    except Exception as e:
        logging.error(f"Ошибка при удалении друга: {e}")
        return False

@connect
def add_move(game_id: int, move_record: dict, session: Session | None = None):
    from thecheckers.redis_base import redis_client
    import json
    redis_client.rpush(f"game:{game_id}:moves", json.dumps(move_record))

@connect
def get_game_moves_from_db(game_id, session: Session | None = None):
    from thecheckers.redis_base import redis_client
    import json
    moves = redis_client.lrange(f"game:{game_id}:moves", 0, -1)
    return [json.loads(m.decode('utf-8')) for m in moves]

@connect
def persist_game_data(game_id, session: Session | None = None):
    from thecheckers.redis_base import redis_client
    import json
    from thecheckers.models import Game as DBGame, GameMove
    board_state_key = f"game:{game_id}:board_state"
    moves_key = f"game:{game_id}:moves"
    board_state = redis_client.get(board_state_key)
    db_game = session.query(DBGame).filter(DBGame.game_id == game_id).first()
    if db_game and board_state is not None:
        db_game.board_state = board_state.decode('utf-8')
        session.commit()
    moves = redis_client.lrange(moves_key, 0, -1)
    for move in moves:
        move_record = json.loads(move.decode('utf-8'))
        new_move = GameMove(
            game_id=game_id,
            player=move_record['player'],
            from_x=move_record['from']['x'],
            from_y=move_record['from']['y'],
            to_x=move_record['to']['x'],
            to_y=move_record['to']['y'],
            captured_piece=move_record['captured'],
            promotion=move_record['promotion']
        )
        session.add(new_move)
    session.commit()
    redis_client.delete(board_state_key)
    redis_client.delete(moves_key)

@connect
def get_incoming_game_invitations_db(user: str, session: Session | None = None) -> list:
    records = session.query(GameInvitation).filter_by(to_user=user, status="pending").all()
    invites = []
    for invite in records:
        room = session.query(Room).filter_by(room_id=invite.game_id).first()
        if room:
            invites.append({"from_user": invite.from_user, "game_id": invite.game_id})
        else:
            session.delete(invite)
            session.commit()
    return invites

@connect
def create_room_db(room_id, creator, delete_flag, session: Session | None = None):
    room = Room(room_id=room_id, room_creator=creator, delete_after_start=delete_flag)
    session.add(room)
    session.commit()
    return room

@connect
def get_room_by_room_id_db(room_id, session: Session | None = None):
    return session.query(Room).filter_by(room_id=room_id).first()

@connect
def update_room_occupant_db(room_id, occupant_login, session: Session | None = None):
    room = session.query(Room).filter_by(room_id=room_id).first()
    if not room:
        return None
    room.occupant = occupant_login
    session.commit()
    return room

@connect
def update_room_game_db(room_id, new_game_id, session: Session | None = None):
    room = session.query(Room).filter_by(room_id=room_id).first()
    if not room:
        return None
    room.game_id = new_game_id
    session.commit()
    return room

@connect
def leave_room_db(room_id, user, session: Session | None = None):
    room = session.query(Room).filter_by(room_id=room_id).first()
    if not room:
        return False
    if room.room_creator == user:
        if room.occupant:
            room.room_creator = room.occupant
            room.occupant = None
            session.commit()
            return True
        else:
            session.delete(room)
            session.commit()
            return True
    elif room.occupant == user:
        room.occupant = None
        session.commit()
        return True
    return False

@connect
def delete_room_db(room_id, session: Session | None = None):
    room = session.query(Room).filter_by(room_id=room_id).first()
    if room:
        session.delete(room)
        session.commit()
        return True
    return False

@connect
def kick_user_from_room_db(room_id, kicked_user, session: Session | None = None):
    room = session.query(Room).filter_by(room_id=room_id).first()
    if not room:
        return False
    if room.room_creator == kicked_user:
        return False
    if room.occupant == kicked_user:
        room.occupant = None
        session.commit()
        return True
    return False

@connect
def transfer_room_leadership_db(room_id, new_leader, session: Session | None = None):
    room = session.query(Room).filter_by(room_id=room_id).first()
    if not room:
        return False
    if room.occupant != new_leader:
        return False
    old_leader = room.room_creator
    room.room_creator = new_leader
    room.occupant = old_leader
    session.commit()
    return True

@connect
def get_outgoing_game_invitations_db(user: str, room_id: int, session: Session | None = None):
    records = session.query(GameInvitation).filter(
        GameInvitation.from_user == user,
        GameInvitation.game_id == room_id,
        GameInvitation.status.in_(["pending", "declined"])
    ).all()
    return {r.to_user: r.status for r in records}

@connect
def toggle_room_color_choice(room_id: int, user: str, color: str, session: Session | None = None):
    room = session.query(Room).filter_by(room_id=room_id).first()
    if not room:
        return {"error": "Комната не найдена"}
    if user not in [room.room_creator, room.occupant]:
        return {"error": "Нет прав для выбора цвета"}
    if color == "w":
        if room.chosen_white == user:
            room.chosen_white = None
            session.commit()
            return {"chosen_white": room.chosen_white, "chosen_black": room.chosen_black}
        else:
            if room.chosen_white is not None and room.chosen_white != user:
                return {"error": "Белый цвет уже занят"}
            if room.chosen_black == user:
                room.chosen_black = None
            room.chosen_white = user
            session.commit()
            return {"chosen_white": room.chosen_white, "chosen_black": room.chosen_black}
    elif color == "b":
        if room.chosen_black == user:
            room.chosen_black = None
            session.commit()
            return {"chosen_white": room.chosen_white, "chosen_black": room.chosen_black}
        else:
            if room.chosen_black is not None and room.chosen_black != user:
                return {"error": "Черный цвет уже занят"}
            if room.chosen_white == user:
                room.chosen_white = None
            room.chosen_black = user
            session.commit()
            return {"chosen_white": room.chosen_white, "chosen_black": room.chosen_black}
    else:
        return {"error": "Неверный цвет"}

@connect
def get_room_by_user(username, session=None):
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    room_obj = session.query(Room).filter(
        (Room.room_creator == username) | (Room.occupant == username)
    ).first()

    if close_session:
        session.close()
    return room_obj

@connect
def update_room_delete_flag(room_id: int, delete_flag: bool, session: Session | None = None):
    room = session.query(Room).filter_by(room_id=room_id).first()
    if not room:
         return {"error": "Комната не найдена"}
    room.delete_after_start = delete_flag
    session.commit()
    return {"delete_after_start": room.delete_after_start}

@connect
def delete_room_if_flag_set(room_id: int, session: Session | None = None):
    room = session.query(Room).filter_by(room_id=room_id).first()
    if room and room.delete_after_start:
         session.delete(room)
         session.commit()
         return True
    return False

@connect
def update_user_default_delete_flag(user_login, flag, session: Session | None = None):
    session.execute(
        update(Player)
        .where(Player.login == user_login)
        .values(default_delete_after_start=flag)
    )
    session.commit()
