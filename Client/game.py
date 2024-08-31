class Game:
    current_games = []
    unstarted_games = []

    def __init__(self, f_user=None, c_user=None, game_id=None):
        self.f_user = f_user
        self.c_user = c_user
        self.game_id = game_id if game_id is not None else len(self.__class__.current_games) + len(self.__class__.unstarted_games) + 1

        if f_user is None or c_user is None:
            self.__class__.unstarted_games.append(self)
        else:
            self.__class__.current_games.append(self)

    @classmethod
    def get_current_games(cls):
        return cls.current_games

    @classmethod
    def search_game(cls, user_id):
        for game in cls.unstarted_games:
            if game.f_user is None:
                game.f_user = user_id
            elif game.c_user is None:
                game.c_user = user_id

            # если готовы играть перемещаемся в current_games
            if game.f_user is not None and game.c_user is not None:
                cls.unstarted_games.remove(game)
                cls.current_games.append(game)
                return game

        # создаем новую игру, если нет подходящей
        white_user = user_id if cls.assign_user_to_white() else None
        black_user = None if cls.assign_user_to_white() else user_id
        new_game = Game(f_user=white_user, c_user=black_user)
        cls.unstarted_games.append(new_game)
        return new_game

    @staticmethod
    def assign_user_to_white():
        return len(Game.unstarted_games) % 2 == 0

    def __repr__(self):
        return f"Game(f_user={self.f_user}, c_user={self.c_user}, game_id={self.game_id})"

    @classmethod
    def end_game(cls, game_id):
        game_to_remove = None
        for game in cls.current_games:
            if game.game_id == game_id:
                game_to_remove = game
                break

        if game_to_remove:
            cls.current_games.remove(game_to_remove)
            print(f"Game {game_id} has ended and been removed.")
        else:
            print(f"Game {game_id} is not in the list of current games.")

    def display_board(self, player_id):
        if player_id == self.f_user:
            # Возвращается доска, где белые внизу
            pass
        elif player_id == self.c_user:
            # Возвращается доска, где чёрные внизу
            pass

