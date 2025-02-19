let pieces = [
    {"color":1,"x":1,"y":0,"mode":"p"},
    {"color":1,"x":3,"y":0,"mode":"p"},
    {"color":1,"x":5,"y":0,"mode":"p"},
    {"color":1,"x":7,"y":0,"mode":"p"},
    {"color":1,"x":0,"y":1,"mode":"p"},
    {"color":1,"x":2,"y":1,"mode":"p"},
    {"color":1,"x":4,"y":1,"mode":"p"},
    {"color":1,"x":6,"y":1,"mode":"p"},
    {"color":1,"x":1,"y":2,"mode":"p"},
    {"color":1,"x":3,"y":2,"mode":"p"},
    {"color":1,"x":5,"y":2,"mode":"p"},
    {"color":1,"x":7,"y":2,"mode":"p"},
    {"color":0,"x":0,"y":7,"mode":"p"},
    {"color":0,"x":2,"y":7,"mode":"p"},
    {"color":0,"x":4,"y":7,"mode":"p"},
    {"color":0,"x":6,"y":7,"mode":"p"},
    {"color":0,"x":1,"y":6,"mode":"p"},
    {"color":0,"x":3,"y":6,"mode":"p"},
    {"color":0,"x":5,"y":6,"mode":"p"},
    {"color":0,"x":7,"y":6,"mode":"p"},
    {"color":0,"x":0,"y":5,"mode":"p"},
    {"color":0,"x":2,"y":5,"mode":"p"},
    {"color":0,"x":4,"y":5,"mode":"p"},
    {"color":0,"x":6,"y":5,"mode":"p"}
];

let current_player = 'w';
let must_capture_piece = null;
let selected_piece = null;
let possibleMoves = [];
let movesList = [];
let game_over = false;
let USE_INTERNAL_LABELS = false;
let lastMoveCount = 0;
let CANVAS, CTX;
let CELL_SIZE, BOARD_OFFSET_X, BOARD_OFFSET_Y;
let difficulty = 'hard';
let user_color = 'w';
let IS_SELECTED = false;
let colors = {1: "rgb(0, 0, 0)", 0: "rgb(255, 255, 255)"};
let b_colors = {1: "#971616", 0: "#971616"};
let lastFrom = null, lastTo = null;
let botFrom = null, botTo = null;
let selected_pos = null;
let LABEL_PADDING = 36;
let boardStates = [];
let currentView = null;
let historyViewMode = false;
let currentPiecesSnapshot = null;
let username = window.username || "ghost1";
let is_ghost = window.is_ghost || false;
let user_color_num = 0;
let bot_color = 'b';
let bot_color_num = 1;
let transpositionTable = {};

let moveRepetition = {
    'w': {},
    'b': {}
};

let userTurnTimer = null;

function hashPosition(pcs, mustCapturePieceLoc, depth, maximizingPlayer) {
    return JSON.stringify({ pcs, mustCapturePieceLoc, depth, maximizingPlayer });
}

function quiescenceSearch(pcs, alpha, beta, maximizingPlayer) {
    let standPat = evaluatePosition(pcs);
    if (maximizingPlayer) {
        if (standPat >= beta) return beta;
        if (alpha < standPat) alpha = standPat;
    } else {
        if (standPat <= alpha) return alpha;
        if (beta > standPat) beta = standPat;
    }
    let color = maximizingPlayer ? 1 : 0;
    let moves = generateAllMoves(pcs, color, null).filter(move => {
        let sel_piece = get_piece_at(pcs, move.from.x, move.from.y);
        let res = validate_move(sel_piece, move.to, maximizingPlayer ? 'b' : 'w', pcs, null);
        return res.captured;
    });
    moves = orderMoves(moves, pcs, color, null, maximizingPlayer);
    for (let move of moves) {
        let pcsCopy = pcs.map(p => ({ ...p }));
        let res = applyMove(pcsCopy, move, color, null);
        let score;
        if (res.move_result === 'continue_capture') {
            score = quiescenceSearch(res.newPcs, alpha, beta, maximizingPlayer);
        } else {
            score = quiescenceSearch(res.newPcs, alpha, beta, !maximizingPlayer);
        }
        if (maximizingPlayer) {
            if (score > alpha) alpha = score;
            if (alpha >= beta) return beta;
        } else {
            if (score < beta) beta = score;
            if (beta <= alpha) return alpha;
        }
    }
    return maximizingPlayer ? alpha : beta;
}


function initializePieces(userColor) {
    if (userColor === 'w') {
        return [
            {"color":1,"x":1,"y":0,"mode":"p"},
            {"color":1,"x":3,"y":0,"mode":"p"},
            {"color":1,"x":5,"y":0,"mode":"p"},
            {"color":1,"x":7,"y":0,"mode":"p"},
            {"color":1,"x":0,"y":1,"mode":"p"},
            {"color":1,"x":2,"y":1,"mode":"p"},
            {"color":1,"x":4,"y":1,"mode":"p"},
            {"color":1,"x":6,"y":1,"mode":"p"},
            {"color":1,"x":1,"y":2,"mode":"p"},
            {"color":1,"x":3,"y":2,"mode":"p"},
            {"color":1,"x":5,"y":2,"mode":"p"},
            {"color":1,"x":7,"y":2,"mode":"p"},
            {"color":0,"x":0,"y":5,"mode":"p"},
            {"color":0,"x":2,"y":5,"mode":"p"},
            {"color":0,"x":4,"y":5,"mode":"p"},
            {"color":0,"x":6,"y":5,"mode":"p"},
            {"color":0,"x":1,"y":6,"mode":"p"},
            {"color":0,"x":3,"y":6,"mode":"p"},
            {"color":0,"x":5,"y":6,"mode":"p"},
            {"color":0,"x":7,"y":6,"mode":"p"},
            {"color":0,"x":0,"y":7,"mode":"p"},
            {"color":0,"x":2,"y":7,"mode":"p"},
            {"color":0,"x":4,"y":7,"mode":"p"},
            {"color":0,"x":6,"y":7,"mode":"p"}
        ];
    } else {
        return [
            {"color":1,"x":1,"y":0,"mode":"p"},
            {"color":1,"x":3,"y":0,"mode":"p"},
            {"color":1,"x":5,"y":0,"mode":"p"},
            {"color":1,"x":7,"y":0,"mode":"p"},
            {"color":1,"x":0,"y":1,"mode":"p"},
            {"color":1,"x":2,"y":1,"mode":"p"},
            {"color":1,"x":4,"y":1,"mode":"p"},
            {"color":1,"x":6,"y":1,"mode":"p"},
            {"color":1,"x":1,"y":2,"mode":"p"},
            {"color":1,"x":3,"y":2,"mode":"p"},
            {"color":1,"x":5,"y":2,"mode":"p"},
            {"color":1,"x":7,"y":2,"mode":"p"},
            {"color":0,"x":0,"y":5,"mode":"p"},
            {"color":0,"x":2,"y":5,"mode":"p"},
            {"color":0,"x":4,"y":5,"mode":"p"},
            {"color":0,"x":6,"y":5,"mode":"p"},
            {"color":0,"x":1,"y":6,"mode":"p"},
            {"color":0,"x":3,"y":6,"mode":"p"},
            {"color":0,"x":5,"y":6,"mode":"p"},
            {"color":0,"x":7,"y":6,"mode":"p"},
            {"color":0,"x":0,"y":7,"mode":"p"},
            {"color":0,"x":2,"y":7,"mode":"p"},
            {"color":0,"x":4,"y":7,"mode":"p"},
            {"color":0,"x":6,"y":7,"mode":"p"}
        ];
    }
}


function copyPieces(pcs) {
    return pcs.map(p => ({...p}));
}

function serializeMove(move) {
    return `${move.from.x},${move.from.y}->${move.to.x},${move.to.y}`;
}

function saveGameState() {
    let state = {
        pieces: pieces.map(p => ({...p})),
        current_player,
        must_capture_piece,
        game_over,
        difficulty,
        lastFrom,
        lastTo,
        botFrom,
        botTo,
        user_color,
        movesList,
        moveRepetition
    };
    localStorage.setItem('checkers_game_state', JSON.stringify(state));
}

function loadGameState() {
    let stateStr = localStorage.getItem('checkers_game_state');
    if(stateStr) {
        let state = JSON.parse(stateStr);
        pieces = state.pieces;
        current_player = state.current_player;
        must_capture_piece = state.must_capture_piece;
        game_over = state.game_over;
        difficulty = state.difficulty || 'hard';
        lastFrom = state.lastFrom;
        lastTo = state.lastTo;
        botFrom = state.botFrom;
        botTo = state.botTo;
        user_color = state.user_color || 'w';
        movesList = state.movesList || [];
        moveRepetition = state.moveRepetition || { 'w': {}, 'b': {} };

        user_color_num = (user_color === 'w') ? 0 : 1;
        bot_color_num = 1 - user_color_num;
        bot_color = (bot_color_num === 0) ? 'w' : 'b';


        document.getElementById('status').textContent = current_player === 'w' ? 'Ход белых' : 'Ход черных';
        restoreMovesHistory();
        lastMoveCount = movesList.length;
        updateMovesList();
        if (!game_over && current_player === bot_color) {
            setTimeout(makeBotMove, 1000);
        }
    } else {
        movesList = [];
        updateMovesList();
    }
}

function restoreMovesHistory() {
    const movesContainer = document.querySelector('.moves-list');
    movesContainer.innerHTML = '';
    for (let i = 0; i < movesList.length; i++) {
        let move = movesList[i];
        let li = document.createElement('li');
        li.classList.add(move.player === 'w' ? 'player-move' : 'opponent-move');
        li.setAttribute('data-move-index', i);
        let div = document.createElement('div');
        div.classList.add('move-content');
        let sp1 = document.createElement('span');
        sp1.classList.add('move-player');
        sp1.textContent = move.player === 'w' ? username : 'Бот Мастер Манго';
        let sp2 = document.createElement('span');
        sp2.classList.add('move-description');
        let moveText = `${convertPosToNotation(move.from)} -> ${convertPosToNotation(move.to)}`;
        sp2.textContent = moveText;
        if (move.promoted) {
            let crownIcon = document.createElement('i');
            crownIcon.classList.add('fa-solid', 'fa-crown');
            crownIcon.style.marginLeft = '5px';
            sp2.appendChild(crownIcon);
        }
        div.appendChild(sp1);
        div.appendChild(sp2);
        li.appendChild(div);
        movesContainer.appendChild(li);
        li.addEventListener('click', onMoveClick);
    }
    let movesCont = document.querySelector('.moves-container');
    movesCont.scrollTop = movesCont.scrollHeight;
}

function get_piece_at(pcs, x, y) {
    return pcs.find(p => p.x === x && p.y === y) || null;
}

function can_capture(piece, pcs){
    let x = piece.x, y = piece.y;
    let moves = [];
    let color = piece.color;
    let king = piece.is_king;
    if(king){
        let dirs = [[1,1],[1,-1],[-1,1],[-1,-1]];
        for(let [dx, dy] of dirs){
            let opponent_found = false;
            let step = 1;
            while(true){
                let nx = x + dx * step, ny = y + dy * step;
                if(nx < 0 || nx > 7 || ny < 0 || ny > 7) break;
                let pc = get_piece_at(pcs, nx, ny);
                if(pc){
                    if(pc.color !== color && !opponent_found){
                        opponent_found = true;
                    } else {
                        break;
                    }
                } else {
                    if(opponent_found){
                        moves.push({x: nx, y: ny});
                    }
                }
                step++;
            }
        }
    } else {
        let directions = [[2,2],[2,-2],[-2,2],[-2,-2]];
        for(let [dx, dy] of directions){
            let mid_x = x + dx / 2, mid_y = y + dy / 2;
            let end_x = x + dx, end_y = y + dy;
            let captured_piece = get_piece_at(pcs, mid_x, mid_y);
            let target_pos = get_piece_at(pcs, end_x, end_y);
            if(end_x >= 0 && end_x < 8 && end_y >= 0 && end_y < 8 && captured_piece && captured_piece.color !== color && !target_pos){
                moves.push({x: end_x, y: end_y});
            }
        }
    }
    return moves;
}

function can_move(piece, pcs){
    let x = piece.x, y = piece.y;
    let moves = [];
    let color = piece.color;
    let king = piece.is_king;
    if(king){
        let dirs = [[1,1],[1,-1],[-1,1],[-1,-1]];
        for(let [dx, dy] of dirs){
            let step = 1;
            while(true){
                let nx = x + dx * step, ny = y + dy * step;
                if(nx < 0 || nx > 7 || ny < 0 || ny > 7) break;
                if(!get_piece_at(pcs, nx, ny)){
                    moves.push({x: nx, y: ny});
                } else {
                    break;
                }
                step++;
            }
        }
    } else {
        let dirs = color === 0 ? [[-1,-1],[1,-1]] : [[-1,1],[1,1]];
        for(let [dx, dy] of dirs){
            let nx = x + dx, ny = y + dy;
            if(nx >= 0 && nx < 8 && ny >= 0 && ny < 8 && !get_piece_at(pcs, nx, ny)){
                moves.push({x: nx, y: ny});
            }
        }
    }
    return moves;
}

function get_possible_moves(pcs, color, mustCapture = null) {
    let all_moves = {};

    if (mustCapture) {
        let cap = can_capture(mustCapture, pcs);
        if (cap.length > 0) {
            all_moves[`${mustCapture.x},${mustCapture.y}`] = cap;
        }
        return all_moves;
    }

    let any_capture = false;
    for (let p of pcs) {
        if (p.color !== color) continue;
        let cap = can_capture(p, pcs);
        if (cap.length > 0) {
            any_capture = true;
            break;
        }
    }

    for (let p of pcs) {
        if (p.color !== color) continue;
        let moves = [];
        let capMoves = can_capture(p, pcs);
        if (any_capture) {
            moves = capMoves;
        } else {
            let normMoves = can_move(p, pcs);
            moves = capMoves.concat(normMoves);
        }
        all_moves[`${p.x},${p.y}`] = moves;
    }
    return all_moves;
}

function validate_move(selected_piece, new_pos, player, pcs, mustCapturePieceLoc) {
    let color = (player === 'w') ? 0 : 1;
    let valid_moves = get_possible_moves(pcs, color, mustCapturePieceLoc);
    let piece_moves = valid_moves[`${selected_piece.x},${selected_piece.y}`] || [];
    if (!piece_moves.some(m => m.x === new_pos.x && m.y === new_pos.y)) {
        return {move_result: 'invalid'};
    }
    let new_pieces = pcs.map(p => ({...p}));
    let captured = false;
    let captured_pieces = [];
    let x = selected_piece.x, y = selected_piece.y;
    let dx = new_pos.x > x ? 1 : -1;
    let dy = new_pos.y > y ? 1 : -1;
    let moved_piece = null;
    if (Math.abs(new_pos.x - x) > 1) {
        let current_x = x + dx, current_y = y + dy;
        while (current_x !== new_pos.x && current_y !== new_pos.y) {
            let pch = get_piece_at(new_pieces, current_x, current_y);
            if (pch && pch.color !== selected_piece.color) {
                new_pieces = new_pieces.filter(pp => (pp.x !== pch.x || pp.y !== pch.y));
                captured = true;
                captured_pieces.push({x: pch.x, y: pch.y});
                break;
            } else if (pch) break;
            current_x += dx;
            current_y += dy;
        }
    }
    let promoted = false;
    for (let p of new_pieces) {
        if (p.x === x && p.y === y) {
            p.x = new_pos.x;
            p.y = new_pos.y;
            moved_piece = p;
            let was_king = p.is_king;
            if (!p.is_king) {
                if ((p.color === 0 && p.y === 0) || (p.color === 1 && p.y === 7)) {
                    p.is_king = true;
                    p.mode = 'k';
                }
            }
            if (!was_king && p.is_king) {
                promoted = true;
            }
            break;
        }
    }
    let newMustCapture = null;
    if (captured) {
        let cap_moves = can_capture(moved_piece, new_pieces);
        if (cap_moves.length > 0) {
            newMustCapture = {...moved_piece};
            return {
                move_result: 'continue_capture',
                new_pieces,
                captured: true,
                captured_pieces,
                multiple_capture: true,
                newMustCapture,
                promoted
            };
        } else {
            newMustCapture = null;
        }
    } else {
        newMustCapture = null;
    }
    return {
        move_result: 'valid',
        new_pieces,
        captured,
        captured_pieces,
        multiple_capture: false,
        newMustCapture,
        promoted
    };
}

function orderMoves(moves, pcs, color, mustCapturePieceLoc, maximizingPlayer) {
    return moves
        .map(move => {
            let pcsCopy = pcs.map(p => ({ ...p }));
            let res = applyMove(pcsCopy, move, color, mustCapturePieceLoc);
            let heuristicValue = evaluatePosition(res.newPcs);
            if (res.captured) {
                heuristicValue += maximizingPlayer ? 20 : -20;
            }
            if (res.promoted) {
                heuristicValue += maximizingPlayer ? 15 : -15;
            }
            return { move, score: heuristicValue };
        })
        .sort((a, b) => maximizingPlayer ? b.score - a.score : a.score - b.score)
        .map(item => item.move);
}

function switchTurn(){
    current_player = (current_player === 'w' ? 'b' : 'w');
    document.getElementById('status').textContent = (current_player === 'w' ? 'Ход белых' : 'Ход черных');
    updateTurnTimer();
}

function isGameOver(){
    if(game_over) return true;

    let allKings = pieces.every(p => p.is_king);
    if(allKings) {
        endGame('draw_kings');
        return true;
    }

    let color_num = (current_player === 'w') ? 0 : 1;
    let moves = get_possible_moves(pieces, color_num, must_capture_piece);
    let canMove = false;
    for(let k in moves){ if(moves[k].length > 0){ canMove = true; break; } }
    if(!canMove) return true;

    let opponentColor = (current_player === 'w') ? 1 : 0;
    let oppPieces = pieces.filter(p => p.color === opponentColor);
    if(oppPieces.length === 0) return true;

    return false;
}

function endGame(forceStatus = null){
    game_over = true;
    clearTimeout(userTurnTimer);
    let msg;
    let color = (current_player === 'w' ? 0 : 1);
    let moves = get_possible_moves(pieces, color, must_capture_piece);
    let canMove = false;
    for(let k in moves){ if(moves[k].length > 0){ canMove = true; break; } }
    let opponentColor = (current_player === 'w') ? 1 : 0;
    let oppPieces = pieces.filter(p => p.color === opponentColor);

    if(forceStatus){
        if(forceStatus === 'w3') msg = 'Победили белые!';
        else if(forceStatus === 'b3') msg = 'Победили черные!';
        else if(forceStatus === 'draw_kings') msg = 'Ничья: На поле остались только дамки.';
        else if(forceStatus === 'draw_repetition') msg = 'Ничья: Ходы повторяются более 3 раз.';
        else if(forceStatus === 'lose_repetition') msg = `Победили ${current_player === 'w' ? 'черные' : 'белые'}! Игрок ${current_player === 'w' ? 'белые' : 'черные'} повторял ходы.`;
        else msg = 'Ничья!';
    } else {
        if(oppPieces.length === 0){
            msg = (current_player === 'w' ? 'Победили белые!' : 'Победили черные!');
        } else if(!canMove){
            msg = (current_player === 'w' ? 'Победили черные!' : 'Победили белые!');
        } else {
            msg = 'Ничья!';
        }
    }

    document.getElementById('game-over-message').textContent = msg;
    document.getElementById('game-over-modal').style.display = 'flex';
    saveGameState();
}

function returnToMainMenu(){
    window.location.href = '/';
    localStorage.clear()
};

function newGame(){
    localStorage.clear()
    location.reload();
}
function closeModal(id){
    document.getElementById(id).style.display = 'none';
}
function confirmSurrender(){
    closeModal('surrender-modal');
    if(current_player === 'w'){ endGame('b3'); }
    else { endGame('w3'); }
}

function afterPlayerMove(result){
    addMoveToHistory(result, true);
    if (isGameOver()) {
        endGame();
        return;
    }
    let moveStr = serializeMove({from: lastFrom, to: lastTo});
    if(moveRepetition['w'][moveStr]){
        moveRepetition['w'][moveStr] += 1;
    } else {
        moveRepetition['w'][moveStr] = 1;
    }

    if(moveRepetition['w'][moveStr] > 3){
        endGame('lose_repetition');
        return;
    }

    if(isGameOver()){ endGame(); return; }
    if(result.move_result === 'continue_capture'){
        must_capture_piece = result.newMustCapture;
        document.getElementById('status').textContent = (current_player === 'w' ? 'Продолжают ходить белые' : 'Продолжают ходить черные');
        updatePossibleMoves();
        updateTurnTimer();
    } else {
        must_capture_piece = null;
        switchTurn();
        if (isGameOver()) {
            endGame();
            return;
        }
        if(isGameOver()){ endGame(); return; }
        if (current_player === bot_color) { setTimeout(makeBotMove, 1000); }
    }
    saveGameState();
}

function afterBotMove(result){
    addMoveToHistory(result, false);
    if (isGameOver()) {
        endGame();
        return;
    }
    let moveStr = serializeMove({from: botFrom, to: botTo});
    if(moveRepetition['b'][moveStr]){
        moveRepetition['b'][moveStr] += 1;
    } else {
        moveRepetition['b'][moveStr] = 1;
    }

    if(moveRepetition['b'][moveStr] > 3){
        endGame('lose_repetition');
        return;
    }

    if(isGameOver()){ endGame(); return; }
    if(result.move_result === 'continue_capture'){
        must_capture_piece = result.newMustCapture;
        document.getElementById('status').textContent = (current_player === 'w' ? 'Продолжают ходить белые' : 'Продолжают ходить черные');
        setTimeout(makeBotMove, 1000);
    } else {
        must_capture_piece = null;
        switchTurn();
        if (isGameOver()) {
            endGame();
            return;
        }
        if(isGameOver()) endGame();
    }
    saveGameState();
}

function evaluatePosition(pcs) {
    let score = 0;
    let whiteMoves = generateAllMoves(pcs, 0).length;
    let blackMoves = generateAllMoves(pcs, 1).length;

    for (let p of pcs) {
        let pieceValue = p.is_king ? 1.5 : 1;
        let centerX = 3.5, centerY = 3.5;
        let distanceToCenter = Math.sqrt(Math.pow(p.x - centerX, 2) + Math.pow(p.y - centerY, 2));
        let centerControl = (distanceToCenter < 3) ? 0.5 : 0;

        let advancement = 0;
        if (!p.is_king) {
            advancement = p.color === 1 ? p.y : (7 - p.y);
            advancement /= 7;
        }

        let totalValue = pieceValue + centerControl + advancement;
        if (p.color === 1) {
            score += totalValue;
        } else {
            score -= totalValue;
        }
    }

    score += (blackMoves - whiteMoves) * 0.1;

    return score;
}



function generateAllMoves(pcs, color, mustCapturePieceLoc = null) {
    let moves = [];
    let vm = get_possible_moves(pcs, color, mustCapturePieceLoc);
    for (let key in vm) {
        let [px, py] = key.split(',').map(Number);
        let piece = get_piece_at(pcs, px, py);
        for (let m of vm[key]) {
            moves.push({ from: { x: px, y: py }, to: m, piece: piece });
        }
    }
    return moves;
}

function applyMove(pcs, move, currentColor, mustCapturePieceLoc) {
    let selected_piece = get_piece_at(pcs, move.from.x, move.from.y);
    let res = validate_move(selected_piece, move.to, currentColor === 0 ? 'w' : 'b', pcs, mustCapturePieceLoc);
    let newPcs = res.new_pieces;
    let newMustCapture = res.newMustCapture;
    return {newPcs, newMustCapture, move_result: res.move_result};
}

function isTerminalNode(pcs, mustCapturePieceLoc, maximizingPlayer) {
    let color = maximizingPlayer ? 1 : 0;
    let moves = generateAllMoves(pcs, color, mustCapturePieceLoc);
    let opponentColor = maximizingPlayer ? 0 : 1;
    let oppPieces = pcs.filter(p => p.color === opponentColor);
    if (moves.length === 0 || oppPieces.length === 0) {
        return true;
    }
    return false;
}

function minimax(pcs, depth, alpha, beta, maximizingPlayer, mustCapturePieceLoc) {
    let posHash = hashPosition(pcs, mustCapturePieceLoc, depth, maximizingPlayer);
    if (transpositionTable[posHash] !== undefined) {
        return transpositionTable[posHash];
    }
    if (depth === 0 || isTerminalNode(pcs, mustCapturePieceLoc, maximizingPlayer)) {
        let evalScore = evaluatePosition(pcs);
        evalScore = quiescenceSearch(pcs, alpha, beta, maximizingPlayer);
        return { score: evalScore };
    }

    let color = maximizingPlayer ? 1 : 0;
    let moves = generateAllMoves(pcs, color, mustCapturePieceLoc);

    if (moves.length === 0) {
        let evalScore = evaluatePosition(pcs);
        transpositionTable[posHash] = { score: evalScore };
        return { score: evalScore };
    }

    moves = orderMoves(moves, pcs, color, mustCapturePieceLoc, maximizingPlayer);

    let value = maximizingPlayer ? -Infinity : Infinity;
    let bestMoves = [];

    for (let move of moves) {
        let pcsCopy = pcs.map(p => ({ ...p }));
        let res = applyMove(pcsCopy, move, color, mustCapturePieceLoc);
        let nextMustCapture = res.newMustCapture;

        let result;
        if (res.move_result === 'continue_capture') {
            result = minimax(res.newPcs, depth - 1, alpha, beta, maximizingPlayer, nextMustCapture);
        } else {
            result = minimax(res.newPcs, depth - 1, alpha, beta, !maximizingPlayer, null);
        }

        if (maximizingPlayer) {
            if (result.score > value) {
                value = result.score;
                bestMoves = [move];
            } else if (result.score === value) {
                bestMoves.push(move);
            }
            alpha = Math.max(alpha, value);
            if (alpha >= beta) break;
        } else {
            if (result.score < value) {
                value = result.score;
                bestMoves = [move];
            } else if (result.score === value) {
                bestMoves.push(move);
            }
            beta = Math.min(beta, value);
            if (beta <= alpha) break;
        }
    }

    let chosenMove = bestMoves.length > 0 ? bestMoves[Math.floor(Math.random() * bestMoves.length)] : null;
    let retVal = { score: value, move: chosenMove };
    transpositionTable[posHash] = retVal;
    return retVal;
}

function iterativeDeepening(pcs, maxDepth, maximizingPlayer, mustCapturePieceLoc) {
    let bestResult = null;
    for (let d = 1; d <= maxDepth; d++) {
        bestResult = minimax(pcs, d, -Infinity, Infinity, maximizingPlayer, mustCapturePieceLoc);
    }
    return bestResult;
}

function makeBotMove() {
    if (current_player !== bot_color || game_over) return;
    let depth = 4;

    let maximizingPlayer = (bot_color_num === 1);

    let result = minimax(pieces.map(p => ({...p})), depth, -Infinity, Infinity, maximizingPlayer, must_capture_piece);
    let chosen_move = result.move;
    if (!chosen_move) {
        endGame();
        return;
    }

    botFrom = {x: chosen_move.from.x, y: chosen_move.from.y};
    botTo = {x: chosen_move.to.x, y: chosen_move.to.y};
    let sel_piece = get_piece_at(pieces, chosen_move.from.x, chosen_move.from.y);
    let res = validate_move(sel_piece, chosen_move.to, bot_color, pieces, must_capture_piece);
    if(res.move_result === 'invalid'){
        console.error("Бот выбрал неверный ход");
        endGame();
        return;
    }
    pieces = res.new_pieces;
    if(res.move_result === 'continue_capture'){
        must_capture_piece = res.newMustCapture;
    } else {
        must_capture_piece = null;
    }
    afterBotMove(res);
    saveGameState();
}


function addMoveToHistory(result, playerMove = true){
    let player;
    if(playerMove){
        player = current_player;
        if(lastFrom && lastTo){
            movesList.push({
                player: player,
                from: lastFrom,
                to: lastTo,
                captured: result.captured || false,
                promoted: result.promoted || false,
                piecesSnapshot: copyPieces(pieces)
            });
        }
    } else {
        player = bot_color;
        if(botFrom && botTo){
            movesList.push({
                player: player,
                from: botFrom,
                to: botTo,
                captured: result.captured || false,
                promoted: result.promoted || false,
                piecesSnapshot: copyPieces(pieces)
            });
        }
    }
    let movesCont = document.querySelector('.moves-container');
    movesCont.scrollTop = movesCont.scrollHeight;
    saveGameState();
    updateMovesList();
}

function convertPosToNotation(pos){
    let letters = ['A','B','C','D','E','F','G','H'];
    let file = letters[pos.x];
    let rank;

    if (user_color === 'w') {
        rank = 8 - pos.y;
    } else {
        rank = pos.y + 1;
    }

    return file + rank;
}

function onClick(evt){
    if (game_over || current_player === bot_color || historyViewMode || (window.innerWidth <= 1000 && currentView !== null)) {
        return;
    }
    let loc = {x: evt.offsetX, y: evt.offsetY};
    let coords = getCoordinates(loc);
    if(coords.x === -1 || coords.y === -1) return;
    if(!selected_piece){
        let p = get_piece_at(pieces, coords.x, coords.y);
        if (p && p.color === user_color_num && current_player === user_color) { selected_piece = p; IS_SELECTED = true; updatePossibleMoves(); }
    } else {
        let move = possibleMoves.find(m => m.x === coords.x && m.y === coords.y);
        if(move){
            lastFrom = {x: selected_piece.x, y: selected_piece.y};
            lastTo = {x: coords.x, y: coords.y};
            selected_pos = {x: coords.x, y: coords.y};
            let res = validate_move(selected_piece, move, user_color, pieces, must_capture_piece);
            if(res.move_result === 'invalid'){ selected_piece = null; IS_SELECTED = false; possibleMoves = []; return; }
            pieces = res.new_pieces;
            if(res.move_result === 'continue_capture'){
                must_capture_piece = res.newMustCapture;
                selected_piece = get_piece_at(pieces, coords.x, coords.y);
                IS_SELECTED = true;
                updatePossibleMoves();
                afterPlayerMove(res);
            } else if(res.move_result === 'valid'){
                must_capture_piece = null;
                selected_piece = null; IS_SELECTED = false; possibleMoves = [];
                afterPlayerMove(res);
            }
        } else {
            selected_piece = null; IS_SELECTED = false; possibleMoves = [];
        }
    }
    saveGameState();
}

function updatePossibleMoves(){
    if(!selected_piece) return;
    let color = (current_player === 'w') ? 0 : 1;
    let vm = must_capture_piece ? get_possible_moves(pieces, color, must_capture_piece) : get_possible_moves(pieces, color);
    possibleMoves = vm[`${selected_piece.x},${selected_piece.y}`] || [];
}

function getCoordinates(loc){
    let gridX = Math.floor((loc.x - BOARD_OFFSET_X) / CELL_SIZE);
    let gridY = Math.floor((loc.y - BOARD_OFFSET_Y) / CELL_SIZE);

    if (user_color === 'b') {
        gridY = 7 - gridY;
    }

    if(gridX < 0 || gridX > 7 || gridY < 0 || gridY > 7) return {x: -1, y: -1};
    if((gridX + gridY) % 2 === 0) return {x: -1, y: -1};
    return {x: gridX, y: gridY};
}

function adjustScreen() {
    const screenWidth = window.innerWidth;
    const screenHeight = window.innerHeight;
    let size;
    if (screenWidth <= 800) {
        LABEL_PADDING = 0;
        USE_INTERNAL_LABELS = true;
        const mobileHistoryHeight = document.getElementById('mobile-moves-history')?.clientHeight || 0;
        const mobileBarHeight = document.getElementById('mobile-bar')?.clientHeight || 0;
        const reservedSpace = 150;
        const availableHeight = screenHeight - mobileHistoryHeight - mobileBarHeight - reservedSpace;
        size = Math.min(screenWidth, availableHeight);
    } else {
        USE_INTERNAL_LABELS = false;
        if (screenWidth <= 1000) {
            size = Math.min(screenWidth * 0.65, screenHeight * 0.65);
            LABEL_PADDING = 36;
            USE_INTERNAL_LABELS = false;
        } else if (screenWidth <= 1200) {
            size = Math.min(screenWidth * 0.50, screenHeight * 0.50);
            LABEL_PADDING = 30;
            USE_INTERNAL_LABELS = false;
        } else if (screenWidth <= 1400) {
            size = Math.min(screenWidth * 0.60, screenHeight * 0.60);
            LABEL_PADDING = 30;
            USE_INTERNAL_LABELS = false;
        } else {
            size = Math.min(screenWidth * 0.75, screenHeight * 0.75);
            LABEL_PADDING = 36;
            USE_INTERNAL_LABELS = false;
        }
        size = Math.max(300, Math.min(size, 800));
    }
    const dpr = window.devicePixelRatio || 1;
    size = Math.floor(size);
    CTX.setTransform(1, 0, 0, 1, 0, 0);
    CANVAS.width = (size + LABEL_PADDING * 2) * dpr;
    CANVAS.height = (size + LABEL_PADDING * 2) * dpr;
    CANVAS.style.width = (size + LABEL_PADDING * 2) + 'px';
    CANVAS.style.height = (size + LABEL_PADDING * 2) + 'px';
    CTX.scale(dpr, dpr);
    CELL_SIZE = size / 8;
    BOARD_OFFSET_X = LABEL_PADDING;
    BOARD_OFFSET_Y = LABEL_PADDING;
    CTX.clearRect(0, 0, CANVAS.width / dpr, CANVAS.height / dpr);
}

function draw_circle(x, y, r, width, strokeColor, fillColor) {
    const centerX = Math.round(x);
    const centerY = Math.round(y);
    CTX.beginPath();
    CTX.arc(centerX, centerY, r, 0, 2 * Math.PI, false);
    if (fillColor) {
        CTX.fillStyle = fillColor;
        CTX.fill();
    }
    if (strokeColor) {
        CTX.strokeStyle = strokeColor;
        CTX.lineWidth = width;
        CTX.stroke();
    }
    CTX.closePath();
}

function draw_piece(piece, user_color) {
    let fillStyle = colors[piece.color];
    let strokeStyle = colors[piece.color ? 0 : 1];
    let displayX = piece.x;
    let displayY = (user_color === 'b') ? 7 - piece.y : piece.y;
    const X = Math.round(BOARD_OFFSET_X + CELL_SIZE * (displayX + 0.5));
    const Y = Math.round(BOARD_OFFSET_Y + CELL_SIZE * (displayY + 0.5));
    let pieceScale = 1;
    if (window.innerWidth <= 400) {
        pieceScale = 0.90;
    }
    const radius = (CELL_SIZE / 2) * 0.8 * pieceScale;
    const innerRadius = radius * 0.7;
    const crownRadius = radius * 0.5;
    const outerStroke = CELL_SIZE * 0.05 * pieceScale;
    const innerStroke = CELL_SIZE * 0.05 * pieceScale;
    const crownStroke = CELL_SIZE * 0.07 * pieceScale;
    const selectionLineWidth = CELL_SIZE * 0.07 * pieceScale;
    const selectionShadowBlur = CELL_SIZE * 0.3 * pieceScale;
    draw_circle(X, Y, radius, outerStroke, strokeStyle, fillStyle);
    draw_circle(X, Y, innerRadius, innerStroke, strokeStyle, null);
    if (piece.is_king) {
        CTX.beginPath();
        CTX.arc(X, Y, crownRadius, 0, 2 * Math.PI, false);
        CTX.fillStyle = "rgba(255, 215, 0, 0.7)";
        CTX.fill();
        CTX.lineWidth = crownStroke;
        CTX.strokeStyle = "gold";
        CTX.stroke();
        CTX.closePath();
    }
    if (IS_SELECTED && selected_piece === piece) {
        CTX.save();
        CTX.shadowColor = 'rgba(255, 255, 0, 1)';
        CTX.shadowBlur = selectionShadowBlur;
        CTX.beginPath();
        CTX.arc(X, Y, radius * 1.1, 0, 2 * Math.PI, false);
        CTX.strokeStyle = 'yellow';
        CTX.lineWidth = selectionLineWidth;
        CTX.stroke();
        CTX.closePath();
        CTX.restore();
    }
}


function draw_possible_moves() {
    if (historyViewMode || (window.innerWidth <= 1000 && currentView !== null)) return;
    CTX.save();
    const moveLineWidth = CELL_SIZE * 0.05;
    const moveShadowBlur = CELL_SIZE * 0.15;
    CTX.lineWidth = moveLineWidth;
    CTX.strokeStyle = 'rgba(0, 162, 255, 0.8)';
    CTX.shadowColor = 'rgba(0, 162, 255, 0.8)';
    CTX.shadowBlur = moveShadowBlur;

    for (let move of possibleMoves) {
        let displayX = move.x;
        let displayY = (user_color === 'b') ? 7 - move.y : move.y;
        const X = Math.round(BOARD_OFFSET_X + CELL_SIZE * displayX);
        const Y = Math.round(BOARD_OFFSET_Y + CELL_SIZE * displayY);
        CTX.strokeRect(X, Y, CELL_SIZE, CELL_SIZE);
    }
    CTX.restore();
}


function drawLabels() {
    if (!USE_INTERNAL_LABELS) {
        CTX.fillStyle = "#f0f0f0";
        let fontSize = Math.max(12, Math.min(Math.round(CELL_SIZE / 3), 24));
        CTX.font = fontSize + "px Arial";
        CTX.textAlign = "center";
        CTX.textBaseline = "middle";
        const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
        for (let i = 0; i < 8; i++) {
            let x = Math.round(BOARD_OFFSET_X + CELL_SIZE * i + CELL_SIZE / 2);
            let y = Math.round(BOARD_OFFSET_Y - LABEL_PADDING / 2);
            CTX.fillText(letters[i], x, y);
        }
        for (let i = 0; i < 8; i++) {
            const x = BOARD_OFFSET_X + CELL_SIZE * i + CELL_SIZE / 2;
            const y = BOARD_OFFSET_Y + CELL_SIZE * 8 + LABEL_PADDING / 2;
            CTX.fillText(letters[i], x, y);
        }
        for (let i = 0; i < 8; i++) {
            const x = BOARD_OFFSET_X - LABEL_PADDING / 2;
            const y = BOARD_OFFSET_Y + CELL_SIZE * (7 - i) + CELL_SIZE / 2;
            CTX.fillText((i + 1).toString(), x, y);
        }
        for (let i = 0; i < 8; i++) {
            const x = BOARD_OFFSET_X + CELL_SIZE * 8 + LABEL_PADDING / 2;
            const y = BOARD_OFFSET_Y + CELL_SIZE * (7 - i) + CELL_SIZE / 2;
            CTX.fillText((i + 1).toString(), x, y);
        }
    } else {
        CTX.fillStyle = "#f0f0f0";
        let numberFontSize = Math.max(8, CELL_SIZE / 7);
        CTX.font = "bold " + numberFontSize + "px Arial";
        CTX.textAlign = "left";
        CTX.textBaseline = "top";
        for (let i = 0; i < 8; i++) {
            let x = BOARD_OFFSET_X + 3;
            let y = BOARD_OFFSET_Y + CELL_SIZE * i + 3;
            let number = (8 - i).toString();
            CTX.fillText(number, x, y);
        }
        let letterFontSize = Math.max(6, CELL_SIZE / 7);
        CTX.font = "bold " + letterFontSize + "px Arial";
        CTX.textAlign = "right";
        CTX.textBaseline = "bottom";
        const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
        for (let j = 0; j < 8; j++) {
            let x = BOARD_OFFSET_X + CELL_SIZE * (j + 1) - 3;
            let y = BOARD_OFFSET_Y + CELL_SIZE * 8 - 3;
            CTX.fillText(letters[j], x, y);
        }
    }
}

function render_Board() {
    CTX.fillStyle = "#121212";
    CTX.fillRect(0, 0, CANVAS.width / (window.devicePixelRatio || 1), CANVAS.height / (window.devicePixelRatio || 1));
    let step = user_color === "b" ? 1 : 0;
    for (let i = 0; i < 8; i++) {
        for (let j = 0; j < 8; j++) {
            if ((i + j) % 2 === 1) {
                CTX.fillStyle = b_colors[step % 2];
                CTX.fillRect(
                    BOARD_OFFSET_X + CELL_SIZE * j,
                    BOARD_OFFSET_Y + CELL_SIZE * i,
                    CELL_SIZE,
                    CELL_SIZE
                );
            }
            step++;
        }
        step++;
    }
    drawLabels();
}

function render_Pieces(){
    for(let i = 0; i < pieces.length; i++){
        draw_piece(pieces[i], user_color);
    }
    if(IS_SELECTED){
        draw_possible_moves();
    }
}

function update(){
    CTX.clearRect(0, 0, CANVAS.width / (window.devicePixelRatio || 1), CANVAS.height / (window.devicePixelRatio || 1));
    render_Board();
    render_Pieces();
    window.requestAnimationFrame(update);
}

window.addEventListener('resize', () => {
    adjustScreen();
    updateMovesList();
    if (historyViewMode && currentView !== null) {
        if (window.innerWidth <= 1000) {
            let mobileHistoryElem = document.getElementById("mobile-moves-history");
            if (mobileHistoryElem) {
                mobileHistoryElem.querySelectorAll('.move-part')
                    .forEach(el => el.classList.remove('selected'));
                let part = mobileHistoryElem.querySelector(`.move-part[data-index="${currentView}"]`);
                if (part) part.classList.add('selected');
            }
            hideReturnToCurrentButton();
        } else {
            updateDesktopHistorySelection(currentView);
                let historyContainer = document.getElementById('history-view-container');
                if (historyContainer) historyContainer.style.display = 'flex';
                let historyLabel = document.getElementById('history-view-label');
                if (historyLabel) historyLabel.style.display = 'inline';
                showReturnToCurrentButton();
            }
        } else {
            hideReturnToCurrentButton();
        }
});

function updateDesktopHistorySelection(index) {
    const movesListItems = document.querySelectorAll('.moves-list li');
    movesListItems.forEach(li => li.classList.remove('selected'));
    const target = document.querySelector(`.moves-list li[data-move-index="${index}"]`);
    if (target) {
        target.classList.add('selected');
    }
}

window.onload = function(){
    CANVAS = document.getElementById("board");
    CTX = CANVAS.getContext("2d");
    CTX.imageSmoothingEnabled = true;
    adjustScreen();

    user_color = window.user_color || 'w';
    user_color_num = (user_color === 'w') ? 0 : 1;
    bot_color_num = 1 - user_color_num;
    bot_color = (bot_color_num === 0) ? 'w' : 'b';

    let stateStr = localStorage.getItem('checkers_game_state');
    if (stateStr) {
        loadGameState();
    } else {
        pieces = initializePieces(user_color);

        current_player = 'w';
        document.getElementById('status').textContent = (current_player === 'w' ? 'Ход белых' : 'Ход черных');
        saveGameState();

        if (bot_color === 'w') {
            setTimeout(makeBotMove, 1000);
        }
    }


    if(selected_piece) updatePossibleMoves();

    update();
    CANVAS.addEventListener('click', onClick);
    let diffSel = document.getElementById('difficulty-select');
    if(diffSel){
        diffSel.value = difficulty;
        diffSel.addEventListener('change', (e) => {
            difficulty = e.target.value;
            saveGameState();
        });
    }
    if (!game_over && current_player === user_color) {
        updateTurnTimer();
    }
    addEventListeners();
};

function onMoveClick(evt){
    if(!movesList || movesList.length === 0) return;
    const li = evt.currentTarget;
    const index = parseInt(li.getAttribute('data-move-index'), 10);
    if(isNaN(index)) return;
    showHistoryState(index);
}

function showHistoryState(index) {
    if (index === movesList.length - 1) {
        returnToCurrentState();
        return;
    }
    if (!historyViewMode) {
        currentPiecesSnapshot = copyPieces(pieces);
    }
    historyViewMode = true;
    currentView = index;
    let snapshot = movesList[index].piecesSnapshot;
    pieces = copyPieces(snapshot);
    IS_SELECTED = false;
    selected_piece = null;
    possibleMoves = [];
    must_capture_piece = null;

    let historyContainer = document.getElementById('history-view-container');
    if (historyContainer) historyContainer.style.display = 'flex';
    let historyLabel = document.getElementById('history-view-label');
    if (historyLabel) historyLabel.style.display = 'inline';

    showReturnToCurrentButton();
    updateMobileReturnButtonVisibility();

    let movesListItems = document.querySelectorAll('.moves-list li');
    movesListItems.forEach(li => li.classList.remove('selected'));
    let target = document.querySelector(`.moves-list li[data-move-index="${index}"]`);
    if (target) {
        target.classList.add('selected');
        target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (window.innerWidth > 1000) {
        showHistoryViewIndicator();
    } else {
        let mobileIndicator = document.getElementById('history-view-indicator-mobile');
        if (mobileIndicator) mobileIndicator.style.display = 'block';
    }
    update();
}

function returnToCurrentState() {
    document.querySelectorAll('.moves-list li.selected')
        .forEach(li => li.classList.remove('selected'));

    if (!currentPiecesSnapshot) {
        return;
    }

    historyViewMode = false;
    currentView = null;

    pieces = copyPieces(currentPiecesSnapshot);
    currentPiecesSnapshot = null;
    must_capture_piece = null;
    selected_piece = null;
    IS_SELECTED = false;
    possibleMoves = [];

    let historyContainer = document.getElementById('history-view-container');
    if (historyContainer) historyContainer.style.display = 'none';

    let historyLabel = document.getElementById('history-view-label');
    if (historyLabel) historyLabel.style.display = 'none';

    let indicator = document.getElementById('history-view-indicator');
    if (indicator) indicator.style.display = 'none';

    let mobileIndicator = document.getElementById('history-view-indicator-mobile');
    if (mobileIndicator) mobileIndicator.style.display = 'none';

    hideReturnToCurrentButton();
    updateMobileReturnButtonVisibility();
    updatePossibleMoves();
    update();
}

function showReturnToCurrentButton() {
    let btn = document.getElementById('history-view-button');
    if (!btn) return;
    btn.removeEventListener('click', returnToCurrentState);
    btn.addEventListener('click', returnToCurrentState);
    btn.style.display = 'block';
}

function hideReturnToCurrentButton() {
    let btn = document.getElementById('history-view-button');
    if (btn) btn.style.display = 'none';
}

function updateTurnTimer() {
    clearTimeout(userTurnTimer);
    if (current_player === user_color && !game_over) {
        userTurnTimer = setTimeout(() => {
            if (current_player === user_color && !game_over) {
                if (user_color === 'w') endGame('b3');
                else endGame('w3');
            }
        }, 120000);
    }
}


function openMobileSettingsModal() {
    let modal = document.getElementById("mobile-settings-modal");
    if (modal) {
        modal.style.display = "flex";
    }
}

function showHistoryViewIndicator() {
    if (window.innerWidth <= 1000) return;
    let indicator = document.getElementById('history-view-indicator');
    if (!indicator) return;
    indicator.style.display = 'block';
}

function returnToCurrentView() {
    pieces = copyPieces(boardStates[boardStates.length - 1]);
    currentView = null;
    let indicator = document.getElementById('history-view-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
    document.querySelectorAll('.moves-list li').forEach(moveLi => moveLi.classList.remove('selected'));
    let mobileHistoryElem = document.getElementById("mobile-moves-history");
    if (mobileHistoryElem) {
        mobileHistoryElem.querySelectorAll('.move-part').forEach(part => {
            part.classList.remove('selected');
        });
    }
    updateMobileReturnButtonVisibility();
    let mh = document.getElementById("mobile-moves-history");
    if (mh) {
        setTimeout(() => {
            mh.scrollTo({ left: mh.scrollWidth, behavior: 'smooth' });
        }, 100);
    }
}

function viewBoardState(moveIndex) {
    if (moveIndex < 0 || moveIndex > boardStates.length - 1) return;
    if (moveIndex === boardStates.length - 1) {
        returnToCurrentView();
        return;
    }
    if (!historyViewMode) {
        currentPiecesSnapshot = copyPieces(pieces);
    }
    historyViewMode = true;
    currentView = moveIndex;
    pieces = copyPieces(boardStates[moveIndex]);
    showHistoryViewIndicator();
    updateMobileReturnButtonVisibility();
    showReturnToCurrentButton();
    updateMobileHistorySelection();
}

function updateMobileHistorySelection() {
    let mobileHistoryElem = document.getElementById("mobile-moves-history");
    if (!mobileHistoryElem) return;
    let containers = mobileHistoryElem.querySelectorAll('.mobile-move');
    let containerRect = mobileHistoryElem.getBoundingClientRect();
    containers.forEach(container => {
        let parts = container.querySelectorAll('.move-part');
        parts.forEach(part => {
            if (parseInt(part.getAttribute('data-index')) === currentView) {
                part.classList.add('selected');
                let partRect = part.getBoundingClientRect();
                if (partRect.left < containerRect.left || partRect.right > containerRect.right) {
                    part.scrollIntoView({ behavior: 'smooth', inline: 'nearest', block: 'nearest' });
                }
            } else {
                part.classList.remove('selected');
            }
        });
    });
}

function updateMobileReturnButtonVisibility() {
    const btn = document.getElementById('mobile-return-button');
    if (!btn) return;
    if (currentView !== null) {
        btn.classList.add('visible');
    } else {
        btn.classList.remove('visible');
    }
}

function updateMovesList() {
    const movesContainer = document.querySelector('.moves-list');
    let hasNewMoves = movesList.length > lastMoveCount;
    for (let i = lastMoveCount; i < movesList.length; i++) {
        let move = movesList[i];
        let li = document.createElement('li');
        li.classList.add(move.player === 'w' ? 'player-move' : 'opponent-move', 'new-move');
        let moveContent = document.createElement('div');
        moveContent.classList.add('move-content');
        let playerLabel = document.createElement('span');
        playerLabel.classList.add('move-player');
        playerLabel.textContent = move.player === 'w' ? username : 'Бот Мастер Манго';
        let moveDescription = document.createElement('span');
        moveDescription.classList.add('move-description');
        let notationText = convertPosToNotation(move.from) + ' -> ' + convertPosToNotation(move.to);
        moveDescription.textContent = '';
        if (move.promoted) {
            let crownIcon = document.createElement('i');
            crownIcon.classList.add('fa-solid', 'fa-crown');
            crownIcon.style.marginRight = '5px';
            moveDescription.appendChild(crownIcon);
        }
        moveDescription.appendChild(document.createTextNode(notationText));
        moveContent.appendChild(playerLabel);
        moveContent.appendChild(moveDescription);
        li.appendChild(moveContent);
        li.setAttribute('data-move-index', i);
        li.addEventListener('click', () => {
            document.querySelectorAll('.moves-list li').forEach(el => el.classList.remove('selected'));
            li.classList.add('selected');
            if (window.innerWidth > 1000) {
                showHistoryState(i);
            } else {
                viewBoardState(i);
            }
        });
        li.addEventListener('animationend', () => {
            li.classList.remove('new-move');
        });
        movesContainer.appendChild(li);
        boardStates.push(copyPieces(move.piecesSnapshot));
    }
    lastMoveCount = movesList.length;
    let containerBlock = document.querySelector('.moves-container');
    if (hasNewMoves && containerBlock) {
        containerBlock.scrollTop = containerBlock.scrollHeight;
    }
    if (window.innerWidth <= 1000) {
        let mobileHistoryElem = document.getElementById('mobile-moves-history');
        if (!mobileHistoryElem) return;
        const scrollTolerance = 5;
        let wasAtEnd = (
            mobileHistoryElem.scrollLeft + mobileHistoryElem.clientWidth >=
            mobileHistoryElem.scrollWidth - scrollTolerance
        );
        let oldScrollLeft = mobileHistoryElem.scrollLeft;
        mobileHistoryElem.innerHTML = "";
        let groups = [];
        let currentGroup = null;
        for (let i = 0; i < movesList.length; i++) {
            let m = movesList[i];
            if (!currentGroup || m.player !== currentGroup.player) {
                if (currentGroup) groups.push(currentGroup);
                currentGroup = { player: m.player, moves: [m] };
            } else {
                currentGroup.moves.push(m);
            }
        }
        if (currentGroup) groups.push(currentGroup);
        let roundCounter = 1;
        let cumulativeIndex = 0;
        let mobileContainers = [];
        for (let i = 0; i < groups.length; i++) {
            let grp = groups[i];
            let container = document.createElement('span');
            container.classList.add('mobile-move');
            if (i % 2 === 0) {
                let roundLabel = document.createElement('span');
                roundLabel.classList.add('round-label');
                roundLabel.textContent = roundCounter + ".   ";
                roundCounter++;
                container.appendChild(roundLabel);
            }
            for (let j = 0; j < grp.moves.length; j++) {
                let boardStateIndex = cumulativeIndex + j;
                if (j === 0) {
                    let movePart = document.createElement('span');
                    movePart.classList.add('move-part', 'move-text');
                    let textMobile = convertPosToNotation(grp.moves[j].to);
                    movePart.textContent = "";
                    if (grp.moves[j].captured) {
                        movePart.style.fontWeight = 'bold';
                    }
                    if (grp.moves[j].promoted) {
                        let crownIcon = document.createElement('i');
                        crownIcon.classList.add('fa-solid', 'fa-crown');
                        crownIcon.style.marginRight = '3px';
                        movePart.appendChild(crownIcon);
                    }
                    movePart.appendChild(document.createTextNode(textMobile));
                    movePart.setAttribute('data-index', boardStateIndex);
                    movePart.addEventListener('click', function(event) {
                        event.stopPropagation();
                        if (boardStateIndex === boardStates.length - 1) {
                            returnToCurrentView();
                        } else {
                            mobileHistoryElem.querySelectorAll('.move-part').forEach(el => el.classList.remove('selected'));
                            movePart.classList.add('selected');
                            viewBoardState(boardStateIndex);
                        }
                    });
                    container.appendChild(movePart);
                } else {
                    let openParen = document.createElement('span');
                    openParen.textContent = "(";
                    container.appendChild(openParen);
                    let movePart = document.createElement('span');
                    movePart.classList.add('move-part', 'move-text');
                    let textMobile = convertPosToNotation(grp.moves[j].to);
                    movePart.textContent = "";
                    if (grp.moves[j].captured) {
                        movePart.style.fontWeight = 'bold';
                    }
                    if (grp.moves[j].promoted) {
                        let crownIcon = document.createElement('i');
                        crownIcon.classList.add('fa-solid', 'fa-crown');
                        crownIcon.style.marginRight = '3px';
                        movePart.appendChild(crownIcon);
                    }
                    movePart.appendChild(document.createTextNode(textMobile));
                    movePart.setAttribute('data-index', boardStateIndex);
                    movePart.addEventListener('click', function(event) {
                        event.stopPropagation();
                        if (boardStateIndex === boardStates.length - 1) {
                            returnToCurrentView();
                        } else {
                            mobileHistoryElem.querySelectorAll('.move-part').forEach(el => el.classList.remove('selected'));
                            movePart.classList.add('selected');
                            viewBoardState(boardStateIndex);
                        }
                    });
                    container.appendChild(movePart);
                    let closeParen = document.createElement('span');
                    closeParen.textContent = ")";
                    container.appendChild(closeParen);
                }
            }
            let gap = "";
            if (i + 1 < groups.length) {
                gap = (i % 2 === 0) ? "     " : "            ";
            }
            let gapText = document.createTextNode(gap);
            container.appendChild(gapText);
            mobileHistoryElem.appendChild(container);
            mobileContainers.push(container);
            cumulativeIndex += grp.moves.length;
        }
        mobileHistoryElem.scrollLeft = oldScrollLeft;
        if (currentView === null && wasAtEnd) {
            setTimeout(() => {
                mobileHistoryElem.scrollTo({ left: mobileHistoryElem.scrollWidth, behavior: 'smooth' });
            }, 100);
        } else {
            mobileContainers.forEach(container => {
                container.querySelectorAll('.move-part').forEach(part => {
                    if (parseInt(part.getAttribute('data-index')) === currentView) {
                        part.classList.add('selected');
                        container.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
                    }
                });
            });
        }
        let arrow = document.getElementById("mobile-scroll-arrow");
        if (hasNewMoves) {
            if (!wasAtEnd && arrow) {
                arrow.style.display = "block";
            } else if (arrow) {
                arrow.style.display = "none";
            }
        }
    }
    if (historyViewMode && currentView !== null && window.innerWidth > 1000) {
        updateDesktopHistorySelection(currentView);
    }
}


function mobilePrevMove() {
    if (boardStates.length <= 1) return;
    let viewIndex = (currentView === null ? boardStates.length - 1 : currentView);
    if (viewIndex > 0) {
        viewBoardState(viewIndex - 1);
    }
}

function mobileNextMove() {
    if (boardStates.length <= 1) return;
    let viewIndex = (currentView === null ? boardStates.length - 1 : currentView);
    if (viewIndex < boardStates.length - 1) {
        let nextIndex = viewIndex + 1;
        if (nextIndex === boardStates.length - 1) {
            returnToCurrentView();
        } else {
            viewBoardState(nextIndex);
        }
    }
}

function addEventListeners() {
    CANVAS.addEventListener("click", onClick);
    window.addEventListener("resize", () => adjustScreen());
    let mobileReturnBtn = document.getElementById('mobile-return-button');
    if (mobileReturnBtn) {
        mobileReturnBtn.removeEventListener('click', returnToCurrentState);
        mobileReturnBtn.addEventListener('click', returnToCurrentState);
    }

    let mobileSettingsIcon = document.getElementById("mobile-settings-icon");
    if (mobileSettingsIcon) {
        mobileSettingsIcon.addEventListener("click", openMobileSettingsModal);
    }
    let mobilePrevMoveBtn = document.getElementById("mobile-prev-move");
    if (mobilePrevMoveBtn) {
        mobilePrevMoveBtn.addEventListener("click", mobilePrevMove);
    }
    let mobileNextMoveBtn = document.getElementById("mobile-next-move");
    if (mobileNextMoveBtn) {
        mobileNextMoveBtn.addEventListener("click", mobileNextMove);
    }
    let modals = ["surrender-modal", "mobile-settings-modal"];
    for (let id of modals) {
        let modal = document.getElementById(id);
        if (modal) {
            modal.addEventListener("click", function(event) {
                if (event.target === modal) {
                    closeModal(id);
                }
            });
        }
    }
    let mobileHistoryElem = document.getElementById("mobile-moves-history");
    if (mobileHistoryElem) {
        mobileHistoryElem.addEventListener('scroll', function() {
            const scrollTolerance = 5;
            let arrow = document.getElementById("mobile-scroll-arrow");
            if (arrow) {
                if (mobileHistoryElem.scrollLeft + mobileHistoryElem.clientWidth >= mobileHistoryElem.scrollWidth - scrollTolerance) {
                    arrow.style.display = "none";
                } else {
                    arrow.style.display = "block";
                }
            }
        });
    }
}

function give_up(){
    const settingsModal = document.getElementById('mobile-settings-modal');
    if (settingsModal) {
        settingsModal.style.display = "none";
    }
    document.getElementById('surrender-modal').style.display = "flex";
}