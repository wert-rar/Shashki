from datetime import datetime
import logging
import json
from sqlalchemy import select, update, and_, or_, union_all, func, NullPool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.engine.url import URL
from thecheckers import utils
from thecheckers.models import (
    Base, Player, CompletedGames, RememberToken, FriendRelation,
    GameInvitation, Game, Room, GameMove
)

DATABASE_URL = URL.create(
    "postgresql+asyncpg",
    username="postgres",
    password="951753aA.",
    host="localhost",
    database="postgres",
    port="5432"
)

async_session: None | AsyncSession = None


async def async_main(url):
    global async_session
    engine = create_async_engine(url, future=True, echo=False, poolclass=NullPool)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def connect(method):
    """
            A decorator function that establishes a connection to the database and manages the session.
            It wraps the provided method and ensures that the database session is properly initialized, committed, and closed.

            Parameters:
            method (callable): The function to be decorated. This function should accept a database session as a keyword argument.

            Returns:
            wrapper (callable): The decorated function. This function will handle the database session management.
    """

    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            try:
                return await method(*args, session=session)
            except Exception as e:
                await session.rollback()
                raise Exception(f'Ошибка при работе с базой данных: {repr(e)} args:\n{args} kwargs:\n{kwargs}')
            finally:
                await session.close()

    return wrapper

# ----------------------------------------------------------------------------------------------------------------------

@connect
async def check_user_exists(user_login, *, session: AsyncSession):
    result = await session.scalar(select(Player).where(Player.login == user_login))
    return result is not None

@connect
async def register_user(user_login, user_password, *, session: AsyncSession):
    hashed_password = utils.hash_password(user_password)
    try:
        async with session.begin():
            session.add(Player(login=user_login, password=hashed_password))
        return True
    except IntegrityError:
        logging.warning(f"Пользователь с логином '{user_login}' уже существует.")
        return False

@connect
async def authenticate_user(user_login, user_password, *, session: AsyncSession):
    row = await session.scalar(select(Player).where(Player.login == user_login))
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
async def get_user_by_login(user_login, *, session: AsyncSession) -> dict:
    user = await session.scalar(select(Player).where(Player.login == user_login))
    return user.to_dict() if user else None

@connect
async def update_user_rang(user_login, points, *, session: AsyncSession):
    try:
        async with session.begin():
            await session.execute(
                update(Player)
                .where(Player.login == user_login)
                .values(rang=func.coalesce(Player.rang, 0) + points)
            )
    except Exception as e:
        logging.error(f"Ошибка обновления ранга: {e}")

@connect
async def update_user_stats(user_login, wins=0, losses=0, draws=0, *, session: AsyncSession):
    try:
        async with session.begin():
            await session.execute(
                update(Player)
                .where(Player.login == user_login)
                .values(
                    wins=Player.wins + wins,
                    losses=Player.losses + losses,
                    draws=Player.draws + draws
                )
            )
    except Exception as e:
        logging.error(f"Ошибка обновления статистики: {e}")

@connect
async def add_completed_game(user_login, game_id, date_start, rating_before, rating_after, rating_change, result, *, session: AsyncSession):
    try:
        async with session.begin():
            session.add(
                CompletedGames(
                    user_login=user_login,
                    game_id=game_id,
                    date_start=date_start,
                    rating_before=rating_before,
                    rating_after=rating_after,
                    rating_change=rating_change,
                    result=result
                )
            )
    except Exception as e:
        logging.error(f"Ошибка при добавлении завершенной игры: {e}")

@connect
async def get_user_history(user_login, *, session: AsyncSession):
    result = await session.execute(
        select(CompletedGames)
        .where(CompletedGames.user_login == user_login)
        .order_by(CompletedGames.ID.asc())
    )
    games = result.scalars().all()
    return [game.to_dict() for game in games]

@connect
async def update_user_avatar(user_login, filename, *, session: AsyncSession):
    await session.execute(
        update(Player)
        .where(Player.login == user_login)
        .values(avatar_filename=filename)
    )
    await session.commit()

@connect
async def add_remember_token(user_login, token, expires_at, *, session: AsyncSession):
    try:
        session.add(RememberToken(user_login=user_login, token=token, expires_at=expires_at.isoformat()))
        logging.info(f"Токен для пользователя '{user_login}' добавлен.")
        return True
    except Exception as e:
        logging.error(f"Ошибка при добавлении токена: {e}")
        return False

@connect
async def get_user_by_remember_token(token, *, session: AsyncSession):
    row = await session.scalar(select(RememberToken).where(RememberToken.token == token))
    if row:
        expires_at = datetime.fromisoformat(row.expires_at)
        if datetime.now() < expires_at:
            return row.user_login
        else:
            await delete_remember_token(token, session=session)
            return None
    return None

@connect
async def delete_remember_token(token, *, session: AsyncSession):
    try:
        row = await session.scalar(select(RememberToken).where(RememberToken.token == token))
        if row:
            await session.delete(row)
            await session.commit()
            logging.info(f"Токен '{token}' удален.")
    except Exception as e:
        logging.error(f"Ошибка при удалении токена: {e}")

@connect
async def delete_all_remember_tokens(user_login, *, session: AsyncSession):
    try:
        result = await session.execute(select(RememberToken).where(RememberToken.user_login == user_login))
        tokens = result.scalars().all()
        for token in tokens:
            await session.delete(token)
        await session.commit()
        logging.info(f"Все токены для пользователя '{user_login}' удалены.")
    except Exception as e:
        logging.error(f"Ошибка при удалении токенов: {e}")

@connect
async def search_users(query: str, exclude_user: str = None, limit: int = 10, *, session: AsyncSession):
    if not query:
        return []
    try:
        like_query = f"{query}%"
        if exclude_user:
            stmt = select(Player.login).where(
                and_(Player.login.like(like_query), Player.login != exclude_user)
            ).limit(limit)
        else:
            stmt = select(Player.login).where(Player.login.like(like_query)).limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [row for row in rows]
    except Exception as e:
        logging.error(f"Ошибка при поиске пользователей: {e}")
        return []

@connect
async def get_top_players(limit: int = 3, *, session: AsyncSession):
    try:
        result = await session.execute(
            select(Player).order_by(Player.rang.desc()).limit(limit)
        )
        players = result.scalars().all()
        return [player.to_dict() for player in players]
    except Exception as e:
        logging.error(f"Ошибка при получении топ игроков: {e}")
        return []

# ----------------------------------------------------------------------------------------------------------------------

@connect
async def send_game_invite_db(sender: str, receiver: str, game_id: int, *, session: AsyncSession) -> str:
    if sender == receiver:
        return "self_invite"
    result = await session.execute(
        select(GameInvitation).filter_by(from_user=sender, to_user=receiver, game_id=game_id)
    )
    existing = result.scalars().first()
    if existing:
        if existing.status == "pending":
            return "already_sent"
        elif existing.status == "declined":
            existing.status = "pending"
            await session.commit()
            return "sent_again"
    result = await session.execute(
        select(GameInvitation).filter_by(from_user=receiver, to_user=sender, game_id=game_id)
    )
    reverse_existing = result.scalars().first()
    if reverse_existing and reverse_existing.status == "pending":
        return "reverse_already_sent"
    new_invite = GameInvitation(from_user=sender, to_user=receiver, status="pending", game_id=game_id)
    session.add(new_invite)
    await session.commit()
    return "sent"

@connect
async def respond_game_invite_db(from_user: str, to_user: str, game_id: int, response: str, *, session: AsyncSession) -> bool:
    result = await session.execute(
        select(GameInvitation).filter_by(from_user=from_user, to_user=to_user, game_id=game_id, status="pending")
    )
    invite = result.scalars().first()
    if not invite:
        return False
    invite.status = "accepted" if response == "accept" else "declined"
    await session.commit()
    if invite.status == "accepted":
        result = await session.execute(select(Game).filter_by(game_id=game_id))
        db_game = result.scalars().first()
        if db_game and db_game.c_user is None:
            db_game.c_user = to_user
            await session.commit()
    return True

@connect
async def remove_game_invite_by_game_id(game_id: int, *, session: AsyncSession):
    result = await session.execute(
        select(GameInvitation).filter_by(game_id=game_id)
    )
    invites = result.scalars().all()
    for inv in invites:
        await session.delete(inv)
    await session.commit()

@connect
async def send_friend_request_db(sender: str, receiver: str, *, session: AsyncSession) -> str:
    if sender == receiver:
        return "self_request"
    try:
        async with session.begin():
            result = await session.execute(
                select(FriendRelation).filter_by(user_login=sender, friend_login=receiver)
            )
            existing = result.scalars().first()
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
            result = await session.execute(
                select(FriendRelation).filter_by(user_login=receiver, friend_login=sender)
            )
            reverse_existing = result.scalars().first()
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
async def get_incoming_friend_requests_db(user: str, *, session: AsyncSession) -> list:
    result = await session.execute(
        select(FriendRelation).filter_by(friend_login=user, status="pending")
    )
    records = result.scalars().all()
    return [r.user_login for r in records]

@connect
async def respond_friend_request_db(sender: str, receiver: str, response: str, *, session: AsyncSession) -> bool:
    result = await session.execute(
        select(FriendRelation).filter_by(user_login=sender, friend_login=receiver, status="pending")
    )
    record = result.scalars().first()
    if not record:
        return False
    record.status = "accepted" if response == "accept" else "declined" if response == "decline" else record.status
    await session.commit()
    return True

@connect
async def get_friends_db(user: str, *, session: AsyncSession) -> list:
    sent_query = select(FriendRelation.friend_login).where(FriendRelation.user_login == user, FriendRelation.status == "accepted")
    received_query = select(FriendRelation.user_login).where(FriendRelation.friend_login == user, FriendRelation.status == "accepted")
    union_query = union_all(sent_query, received_query)
    result = await session.execute(union_query)
    friends = result.scalars().all()
    return list(set(friends))

@connect
async def remove_friend_db(user: str, friend_username: str, *, session: AsyncSession) -> bool:
    try:
        async with session.begin():
            result = await session.execute(
                select(FriendRelation).filter(
                    or_(
                        and_(FriendRelation.user_login == user, FriendRelation.friend_login == friend_username),
                        and_(FriendRelation.user_login == friend_username, FriendRelation.friend_login == user)
                    )
                )
            )
            relations = result.scalars().all()
            if not relations:
                return False
            for rel in relations:
                await session.delete(rel)
        return True
    except Exception as e:
        logging.error(f"Ошибка при удалении друга: {e}")
        return False

@connect
async def add_move(game_id: int, move_record: dict, *, session: AsyncSession):
    from thecheckers.redis_base import redis_client
    redis_client.rpush(f"game:{game_id}:moves", json.dumps(move_record))

@connect
async def get_game_moves_from_db(game_id, *, session: AsyncSession):
    from thecheckers.redis_base import redis_client
    moves = redis_client.lrange(f"game:{game_id}:moves", 0, -1)
    return [json.loads(m.decode('utf-8')) for m in moves]

@connect
async def persist_game_data(game_id, *, session: AsyncSession):
    from thecheckers.redis_base import redis_client
    board_state_key = f"game:{game_id}:board_state"
    moves_key = f"game:{game_id}:moves"
    board_state = redis_client.get(board_state_key)
    result = await session.execute(select(Game).filter_by(game_id=game_id))
    db_game = result.scalars().first()
    if db_game and board_state is not None:
        db_game.board_state = board_state.decode('utf-8')
        await session.commit()
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
    await session.commit()
    redis_client.delete(board_state_key)
    redis_client.delete(moves_key)

@connect
async def get_incoming_game_invitations_db(user: str, *, session: AsyncSession) -> list:
    result = await session.execute(
        select(GameInvitation).filter_by(to_user=user, status="pending")
    )
    records = result.scalars().all()
    invites = []
    for invite in records:
        room_result = await session.execute(select(Room).filter_by(room_id=invite.game_id))
        room = room_result.scalars().first()
        if room:
            invites.append({"from_user": invite.from_user, "game_id": invite.game_id})
        else:
            await session.delete(invite)
            await session.commit()
    return invites

@connect
async def create_room_db(room_id, creator, delete_flag, *, session: AsyncSession):
    room = Room(room_id=room_id, room_creator=creator, delete_after_start=delete_flag)
    session.add(room)
    await session.commit()
    return room

@connect
async def get_room_by_room_id_db(room_id, *, session: AsyncSession):
    result = await session.execute(select(Room).filter_by(room_id=room_id))
    return result.scalars().first()

@connect
async def update_room_occupant_db(room_id, occupant_login, *, session: AsyncSession):
    result = await session.execute(select(Room).filter_by(room_id=room_id))
    room = result.scalars().first()
    if not room:
        return None
    room.occupant = occupant_login
    await session.commit()
    return room

@connect
async def update_room_game_db(room_id, new_game_id, *, session: AsyncSession):
    result = await session.execute(select(Room).filter_by(room_id=room_id))
    room = result.scalars().first()
    if not room:
        return None
    room.game_id = new_game_id
    await session.commit()
    return room

@connect
async def leave_room_db(room_id, user, *, session: AsyncSession):
    result = await session.execute(select(Room).filter_by(room_id=room_id))
    room = result.scalars().first()
    if not room:
        return False
    if room.room_creator == user:
        if room.occupant:
            room.room_creator = room.occupant
            room.occupant = None
            await session.commit()
            return True
        else:
            await session.delete(room)
            await session.commit()
            return True
    elif room.occupant == user:
        room.occupant = None
        await session.commit()
        return True
    return False

@connect
async def delete_room_db(room_id, *, session: AsyncSession):
    result = await session.execute(select(Room).filter_by(room_id=room_id))
    room = result.scalars().first()
    if room:
        await session.delete(room)
        await session.commit()
        return True
    return False

@connect
async def kick_user_from_room_db(room_id, kicked_user, *, session: AsyncSession):
    result = await session.execute(select(Room).filter_by(room_id=room_id))
    room = result.scalars().first()
    if not room:
        return False
    if room.room_creator == kicked_user:
        return False
    if room.occupant == kicked_user:
        room.occupant = None
        await session.commit()
        return True
    return False

@connect
async def transfer_room_leadership_db(room_id, new_leader, *, session: AsyncSession):
    result = await session.execute(select(Room).filter_by(room_id=room_id))
    room = result.scalars().first()
    if not room:
        return False
    if room.occupant != new_leader:
        return False
    old_leader = room.room_creator
    room.room_creator = new_leader
    room.occupant = old_leader
    await session.commit()
    return True

@connect
async def get_outgoing_game_invitations_db(user: str, room_id: int, *, session: AsyncSession):
    result = await session.execute(
        select(GameInvitation).filter(
            GameInvitation.from_user == user,
            GameInvitation.game_id == room_id,
            GameInvitation.status.in_(["pending", "declined"])
        )
    )
    records = result.scalars().all()
    return {r.to_user: r.status for r in records}

@connect
async def toggle_room_color_choice(room_id: int, user: str, color: str, *, session: AsyncSession):
    result = await session.execute(select(Room).filter_by(room_id=room_id))
    room = result.scalars().first()
    if not room:
        return {"error": "Комната не найдена"}
    if user not in [room.room_creator, room.occupant]:
        return {"error": "Нет прав для выбора цвета"}
    if color == "w":
        if room.chosen_white == user:
            room.chosen_white = None
            await session.commit()
            return {"chosen_white": room.chosen_white, "chosen_black": room.chosen_black}
        else:
            if room.chosen_white is not None and room.chosen_white != user:
                return {"error": "Белый цвет уже занят"}
            if room.chosen_black == user:
                room.chosen_black = None
            room.chosen_white = user
            await session.commit()
            return {"chosen_white": room.chosen_white, "chosen_black": room.chosen_black}
    elif color == "b":
        if room.chosen_black == user:
            room.chosen_black = None
            await session.commit()
            return {"chosen_white": room.chosen_white, "chosen_black": room.chosen_black}
        else:
            if room.chosen_black is not None and room.chosen_black != user:
                return {"error": "Черный цвет уже занят"}
            if room.chosen_white == user:
                room.chosen_white = None
            room.chosen_black = user
            await session.commit()
            return {"chosen_white": room.chosen_white, "chosen_black": room.chosen_black}
    else:
        return {"error": "Неверный цвет"}

@connect
async def get_room_by_user(username, *, session: AsyncSession):
    result = await session.execute(
        select(Room).filter((Room.room_creator == username) | (Room.occupant == username))
    )
    room_obj = result.scalars().first()
    return room_obj

@connect
async def update_room_delete_flag(room_id: int, delete_flag: bool, *, session: AsyncSession):
    result = await session.execute(select(Room).filter_by(room_id=room_id))
    room = result.scalars().first()
    if not room:
         return {"error": "Комната не найдена"}
    room.delete_after_start = delete_flag
    await session.commit()
    return {"delete_after_start": room.delete_after_start}

@connect
async def delete_room_if_flag_set(room_id: int, *, session: AsyncSession):
    result = await session.execute(select(Room).filter_by(room_id=room_id))
    room = result.scalars().first()
    if room and room.delete_after_start:
         await session.delete(room)
         await session.commit()
         return True
    return False

@connect
async def update_user_default_delete_flag(user_login, flag, *, session: AsyncSession):
    await session.execute(
        update(Player)
        .where(Player.login == user_login)
        .values(default_delete_after_start=flag)
    )
    await session.commit()