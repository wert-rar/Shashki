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

let CANVAS, CTX;
let CELL_SIZE, BOARD_OFFSET_X, BOARD_OFFSET_Y;
let difficulty = 'medium';
let user_color = 'w';
let IS_SELECTED = false;
let colors = {1: "rgb(0, 0, 0)", 0: "rgb(255, 255, 255)"};
let b_colors = {1: "#971616", 0: "#971616"};
let lastFrom = null, lastTo = null;
let botFrom = null, botTo = null;
let selected_pos = null;
let LABEL_PADDING = 36;

let historyViewMode = false;
let currentPiecesSnapshot = null;

let username = window.username || "ghost1";
let is_ghost = window.is_ghost || false;

let user_color_num = 0;
let bot_color = 'b';
let bot_color_num = 1;

let moveRepetition = {
    'w': {},
    'b': {}
};

let userTurnTimer = null;

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
        difficulty = state.difficulty || 'medium';
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


        document.getElementById('status').textContent = (current_player === 'w' ? 'Ход белых' : 'Ход черных');
        restoreMovesHistory();

        if (!game_over && current_player === bot_color) {
            setTimeout(makeBotMove, 1000);
        }
    } else {
        movesList = [];
    }
}

function restoreMovesHistory(){
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
        sp1.textContent = move.player === 'w' ? username : 'Бот Батат';
        let sp2 = document.createElement('span');
        sp2.classList.add('move-description');
        sp2.textContent = `${convertPosToNotation(move.from)} -> ${convertPosToNotation(move.to)}`;
        div.appendChild(sp1); div.appendChild(sp2);
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

function get_possible_moves(pcs, color, must_capture = null){
    let all_moves = {};
    for(let p of pcs){
        if(p.color !== color) continue;
        if(must_capture && (p.x !== must_capture.x || p.y !== must_capture.y)) continue;
        let cm = can_capture(p, pcs);
        if(must_capture){
            if(cm.length > 0) all_moves[`${p.x},${p.y}`] = cm;
        } else {
            let nm = can_move(p, pcs);
            all_moves[`${p.x},${p.y}`] = cm.concat(nm);
        }
    }
    return all_moves;
}

function validate_move(selected_piece, new_pos, player, pcs, mustCapturePieceLoc){
    let color = (player === 'w') ? 0 : 1;
    let valid_moves = get_possible_moves(pcs, color, mustCapturePieceLoc);
    let piece_moves = valid_moves[`${selected_piece.x},${selected_piece.y}`] || [];
    if(!piece_moves.some(m => m.x === new_pos.x && m.y === new_pos.y)){
        return {move_result: 'invalid'};
    }
    let new_pieces = pcs.map(p => ({...p}));
    let captured = false;
    let captured_pieces = [];
    let x = selected_piece.x, y = selected_piece.y;
    let dx = new_pos.x > x ? 1 : -1;
    let dy = new_pos.y > y ? 1 : -1;
    let moved_piece = null;
    if(Math.abs(new_pos.x - x) > 1){
        let current_x = x + dx, current_y = y + dy;
        while(current_x !== new_pos.x && current_y !== new_pos.y){
            let pch = get_piece_at(new_pieces, current_x, current_y);
            if(pch && pch.color !== selected_piece.color){
                new_pieces = new_pieces.filter(pp => (pp.x !== pch.x || pp.y !== pch.y));
                captured = true;
                captured_pieces.push({x: pch.x, y: pch.y});
                break;
            } else if(pch) break;
            current_x += dx; current_y += dy;
        }
    }
    for(let p of new_pieces){
        if(p.x === x && p.y === y){
            p.x = new_pos.x; p.y = new_pos.y;
            moved_piece = p;
            if(!p.is_king){
                if((p.color === 0 && p.y === 0) || (p.color === 1 && p.y === 7)){
                    p.is_king = true; p.mode = 'k';
                }
            }
            break;
        }
    }

    let newMustCapture = null;
    if(captured){
        let cap_moves = can_capture(moved_piece, new_pieces);
        if(cap_moves.length > 0){
            newMustCapture = {...moved_piece};
            return{
                move_result: 'continue_capture',
                new_pieces,
                captured: true,
                captured_pieces,
                multiple_capture: true,
                newMustCapture
            };
        } else {
            newMustCapture = null;
        }
    } else {
        newMustCapture = null;
    }

    return{
        move_result: 'valid',
        new_pieces,
        captured,
        captured_pieces,
        multiple_capture: false,
        newMustCapture
    };
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
    document.getElementById('game-over-modal').style.display = 'block';
    saveGameState();
}

function returnToMainMenu(){
    window.location.href = '/';
    localStorage.clear()
}
window.addEventListener('beforeunload', () => {
    localStorage.clear();
});
function newGame(){
    localStorage.clear()
    location.reload();
}
function give_up(){
    document.getElementById('surrender-modal').style.display = 'block';
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
            moves.push({from: {x: px, y: py}, to: m, piece: piece});
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
    if (depth === 0 || isTerminalNode(pcs, mustCapturePieceLoc, maximizingPlayer)) {
        return {score: evaluatePosition(pcs)};
    }

    let color = maximizingPlayer ? 1 : 0;
    let moves = generateAllMoves(pcs, color, mustCapturePieceLoc);

    if (moves.length === 0) {
        return {score: evaluatePosition(pcs)};
    }

    let value = maximizingPlayer ? -Infinity : Infinity;
    let bestMoves = [];

    for (let move of moves) {
        let pcsCopy = pcs.map(p => ({...p}));
        let res = applyMove(pcsCopy, move, color, mustCapturePieceLoc);
        let nextMustCapture = res.newMustCapture;
        let nextPlayer = maximizingPlayer;

        let result;
        if (res.move_result === 'continue_capture') {
            result = minimax(res.newPcs, depth - 1, alpha, beta, nextPlayer, nextMustCapture);
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

    let chosenMove = null;
    if (bestMoves.length > 0) {
        chosenMove = bestMoves[Math.floor(Math.random() * bestMoves.length)];
    }

    return {score: value, move: chosenMove};
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
                piecesSnapshot: copyPieces(pieces)
            });
            let li = document.createElement('li');
            li.classList.add(player === 'w' ? 'player-move' : 'opponent-move');
            li.setAttribute('data-move-index', movesList.length - 1);
            let div = document.createElement('div');
            div.classList.add('move-content');
            let sp1 = document.createElement('span');
            sp1.classList.add('move-player');

            sp1.textContent = username;

            let sp2 = document.createElement('span');
            sp2.classList.add('move-description');
            sp2.textContent = `${convertPosToNotation(lastFrom)} -> ${convertPosToNotation(lastTo)}`;
            div.appendChild(sp1);
            div.appendChild(sp2);
            li.appendChild(div);
            document.querySelector('.moves-list').appendChild(li);
            li.addEventListener('click', onMoveClick);
        }
    } else {
        player = bot_color;
        if(botFrom && botTo){
            movesList.push({
                player: player,
                from: botFrom,
                to: botTo,
                piecesSnapshot: copyPieces(pieces)
            });
            let li = document.createElement('li');
            li.classList.add(player === 'w' ? 'player-move' : 'opponent-move');
            li.setAttribute('data-move-index', movesList.length - 1);
            let div = document.createElement('div');
            div.classList.add('move-content');
            let sp1 = document.createElement('span');
            sp1.classList.add('move-player');

            sp1.textContent = 'Бот Батат';

            let sp2 = document.createElement('span');
            sp2.classList.add('move-description');
            sp2.textContent = `${convertPosToNotation(botFrom)} -> ${convertPosToNotation(botTo)}`;
            div.appendChild(sp1);
            div.appendChild(sp2);
            li.appendChild(div);
            document.querySelector('.moves-list').appendChild(li);
            li.addEventListener('click', onMoveClick);
        }
    }
    let movesCont = document.querySelector('.moves-container');
    movesCont.scrollTop = movesCont.scrollHeight;
    saveGameState();
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
    if (game_over || current_player === bot_color || historyViewMode) return;
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

function adjustScreen(){
    const screenWidth = window.innerWidth;
    const screenHeight = window.innerHeight;
    let size;
    if(screenWidth <= 1024){
        size = Math.min(screenWidth * 0.65, screenHeight * 0.65);
        LABEL_PADDING = 30;
    }
    else if(screenWidth <= 1440){
        size = Math.min(screenWidth * 0.75, screenHeight * 0.75);
        LABEL_PADDING = 36;
    }
    else{
        size = Math.min(screenWidth * 0.75, screenHeight * 0.75);
        LABEL_PADDING = 36;
    }
    size = Math.max(300, Math.min(size, 800));
    const dpr = window.devicePixelRatio || 1;
    size = Math.floor(size);
    CTX.setTransform(1, 0, 0, 1, 0, 0);
    CANVAS.width = (size + LABEL_PADDING * 2) * dpr;
    CANVAS.height = (size + LABEL_PADDING * 2) * dpr;
    CANVAS.style.width = `${size + LABEL_PADDING * 2}px`;
    CANVAS.style.height = `${size + LABEL_PADDING * 2}px`;
    CTX.scale(dpr, dpr);
    CELL_SIZE = size / 8;
    BOARD_OFFSET_X = LABEL_PADDING;
    BOARD_OFFSET_Y = LABEL_PADDING;
    CTX.clearRect(0, 0, CANVAS.width / dpr, CANVAS.height / dpr);
}

function draw_circle(x, y, r, width, strokeColor, fillColor){
    CTX.beginPath();
    CTX.arc(x, y, r, 0, 2 * Math.PI, false);
    if(fillColor){ CTX.fillStyle = fillColor; CTX.fill(); }
    if(strokeColor){ CTX.strokeStyle = strokeColor; CTX.lineWidth = width; CTX.stroke(); }
    CTX.closePath();
}

function draw_piece(piece, user_color_param) {
    let fillStyle = colors[piece.color];
    let strokeStyle = colors[piece.color ? 0 : 1];
    let displayX = piece.x;
    let displayY = user_color_param === "b" ? 7 - piece.y : piece.y;
    const X = BOARD_OFFSET_X + CELL_SIZE * (displayX + 0.5);
    const Y = BOARD_OFFSET_Y + CELL_SIZE * (displayY + 0.5);
    const radius = (CELL_SIZE / 2) * 0.8;
    const innerRadius = radius * 0.7;
    const crownRadius = radius * 0.5;
    draw_circle(X, Y, radius, 3, strokeStyle, fillStyle);
    draw_circle(X, Y, innerRadius, 3, strokeStyle, false);
    if(piece.is_king){
        CTX.beginPath();
        CTX.arc(X, Y, crownRadius, 0, 2 * Math.PI, false);
        CTX.fillStyle = "rgba(255,215,0,0.7)";
        CTX.fill();
        CTX.lineWidth = 6;
        CTX.strokeStyle = "gold";
        CTX.stroke();
        CTX.closePath();
    }
    if(IS_SELECTED && selected_piece === piece){
        CTX.save();
        CTX.shadowColor = 'rgba(255,255,0,1)';
        CTX.shadowBlur = 20;
        CTX.beginPath();
        CTX.arc(X, Y, radius * 1.1, 0, 2 * Math.PI, false);
        CTX.strokeStyle = 'yellow';
        CTX.lineWidth = 5;
        CTX.stroke();
        CTX.closePath();
        CTX.restore();
    }
}

function draw_possible_moves(){
    CTX.save();
    CTX.lineWidth = 4;
    CTX.strokeStyle = 'rgba(0,162,255,0.8)';
    CTX.shadowColor = 'rgba(0,162,255,0.8)';
    CTX.shadowBlur = 10;
    for(let move of possibleMoves){
        let displayY = (user_color === "b") ? 7 - move.y : move.y;
        const X = BOARD_OFFSET_X + CELL_SIZE * move.x;
        const Y = BOARD_OFFSET_Y + CELL_SIZE * displayY;
        CTX.strokeRect(X, Y, CELL_SIZE, CELL_SIZE);
    }
    CTX.restore();
}

function drawLabels(){
    CTX.fillStyle = "#f0f0f0";
    let fontSize = CELL_SIZE / 3;
    fontSize = Math.max(12, Math.min(fontSize, 24));
    CTX.font = `${fontSize}px Arial`;
    CTX.textAlign = "center";
    CTX.textBaseline = "middle";
    const letters = ['A','B','C','D','E','F','G','H'];
    for(let i = 0; i < 8; i++){
        const x = BOARD_OFFSET_X + CELL_SIZE * i + CELL_SIZE / 2;
        const y = BOARD_OFFSET_Y - LABEL_PADDING / 2;
        CTX.fillText(letters[i], x, y);
    }
    for(let i = 0; i < 8; i++){
        const x = BOARD_OFFSET_X + CELL_SIZE * i + CELL_SIZE / 2;
        const y = BOARD_OFFSET_Y + CELL_SIZE * 8 + LABEL_PADDING / 2;
        CTX.fillText(letters[i], x, y);
    }
    for(let i = 0; i < 8; i++){
        const x = BOARD_OFFSET_X - LABEL_PADDING / 2;
        const y = BOARD_OFFSET_Y + CELL_SIZE * (7 - i) + CELL_SIZE / 2;
        CTX.fillText(i + 1, x, y);
    }
    for(let i = 0; i < 8; i++){
        const x = BOARD_OFFSET_X + CELL_SIZE * 8 + LABEL_PADDING / 2;
        const y = BOARD_OFFSET_Y + CELL_SIZE * (7 - i) + CELL_SIZE / 2;
        CTX.fillText(i + 1, x, y);
    }
}

function render_Board(){
    CTX.fillStyle = "#121212";
    CTX.fillRect(0, 0, CANVAS.width / (window.devicePixelRatio || 1), CANVAS.height / (window.devicePixelRatio || 1));
    let step = 0;
    for(let i = 0; i < 8; i++){
        for(let j = 0; j < 8; j++){
            let row = (user_color === "b") ? 7 - i : i;
            if ((j + row) % 2 === 1) {
                CTX.fillStyle = b_colors[step % 2];
                CTX.fillRect(BOARD_OFFSET_X + CELL_SIZE * j, BOARD_OFFSET_Y + CELL_SIZE * i, CELL_SIZE, CELL_SIZE);
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
});

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
};

function onMoveClick(evt){
    if(!movesList || movesList.length === 0) return;
    const li = evt.currentTarget;
    const index = parseInt(li.getAttribute('data-move-index'), 10);
    if(isNaN(index)) return;
    showHistoryState(index);
}

function showHistoryState(index) {
    if (!historyViewMode) {
        currentPiecesSnapshot = copyPieces(pieces);
    }
    historyViewMode = true;

    let snapshot = movesList[index].piecesSnapshot;
    pieces = copyPieces(snapshot);
    IS_SELECTED = false;
    selected_piece = null;
    possibleMoves = [];
    must_capture_piece = null;

    let historyContainer = document.getElementById('history-view-container');
    historyContainer.style.display = 'flex';

    let historyLabel = document.getElementById('history-view-label');
    historyLabel.style.display = 'inline';

    showReturnToCurrentButton();

    update();
}

function returnToCurrentState() {
    if (!currentPiecesSnapshot) return;
    historyViewMode = false;
    pieces = copyPieces(currentPiecesSnapshot);
    currentPiecesSnapshot = null;
    must_capture_piece = null;
    selected_piece = null;
    IS_SELECTED = false;
    possibleMoves = [];

    let historyContainer = document.getElementById('history-view-container');
    historyContainer.style.display = 'none';

    let historyLabel = document.getElementById('history-view-label');
    historyLabel.style.display = 'none';

    hideReturnToCurrentButton();

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