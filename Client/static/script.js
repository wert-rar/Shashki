let CANVAS = null;
let CTX = null;
let SELECTED_PIECE = null;
let IS_SELECTED = false;
let CELL_SIZE = 0;
let BOARD_OFFSET_X = 0;
let BOARD_OFFSET_Y = 0;
let CURRENT_STATUS = "w1";
let SERVER_IP = "";
let LABEL_PADDING = 36;
let lastMoveCount = 0;

let boardStates = [];
let currentView = null;


let status = {
  w1: "Ход белых",
  b1: "Ход черных",
  w2: "Нельзя двигать фигуру, сейчас ход белых",
  b2: "Нельзя двигать фигуру, сейчас ход черных",
  w3: "Победили белые",
  b3: "Победили черные",
  w4: "Белые продолжают ход",
  b4: "Черные продолжают ход",
  n: "Ничья!",
  e1: "Ошибка при запросе к серверу",
};

let colors = {
  1: "rgb(0, 0, 0)",
  0: "rgb(255, 255, 255)",
};

let b_colors = {
  1: "#971616",
  0: "#971616",
};

let pieces = [
  { color: 1, x: 1, y: 0, mode: "p" },
  { color: 1, x: 3, y: 0, mode: "p" },
  { color: 1, x: 5, y: 0, mode: "p" },
  { color: 1, x: 7, y: 0, mode: "p" },
  { color: 1, x: 0, y: 1, mode: "p" },
  { color: 1, x: 2, y: 1, mode: "p" },
  { color: 1, x: 4, y: 1, mode: "p" },
  { color: 1, x: 6, y: 1, mode: "p" },
  { color: 1, x: 1, y: 2, mode: "p" },
  { color: 1, x: 3, y: 2, mode: "p" },
  { color: 1, x: 5, y: 2, mode: "p" },
  { color: 1, x: 7, y: 2, mode: "p" },
  { color: 0, x: 0, y: 5, mode: "p" },
  { color: 0, x: 2, y: 5, mode: "p" },
  { color: 0, x: 4, y: 5, mode: "p" },
  { color: 0, x: 6, y: 5, mode: "p" },
  { color: 0, x: 1, y: 6, mode: "p" },
  { color: 0, x: 3, y: 6, mode: "p" },
  { color: 0, x: 5, y: 6, mode: "p" },
  { color: 0, x: 7, y: 6, mode: "p" },
  { color: 0, x: 0, y: 7, mode: "p" },
  { color: 0, x: 2, y: 7, mode: "p" },
  { color: 0, x: 4, y: 7, mode: "p" },
  { color: 0, x: 6, y: 7, mode: "p" },
];

let possibleMoves = [];

function translate(pieces_data) {
  return pieces_data.map(piece => ({
    color: piece.color,
    x: 7 - piece.x,
    y: 7 - piece.y,
    mode: piece.mode,
    is_king: piece.is_king,
  }));
}

function update_data(data) {
    CURRENT_STATUS = data.status_;
    CURRENT_PLAYER = data.current_player;
    let previousSelectedPiece = SELECTED_PIECE ? { ...SELECTED_PIECE } : null;

    if (currentView === null) {
        pieces = data.pieces;
        if (user_color == "b") pieces = translate(pieces);
    }
    document.getElementById("status").innerHTML = status[CURRENT_STATUS];

    if (data.draw_response && data.draw_response !== null) {
        if (data.draw_response === 'accept') {
            displayGameOverMessage(data);
        } else if (data.draw_response === 'decline') {
            showNotification('Ваше предложение ничьей было отклонено.', 'error');
        }
    }

    if (data.draw_offer && data.draw_offer !== null) {
        if (data.draw_offer !== user_color) {
            let modal = document.getElementById("draw-offer-modal");
            modal.style.display = "block";
        }
    } else {
        document.getElementById("draw-offer-modal").style.display = "none";
    }

    if (CURRENT_STATUS === "w3" || CURRENT_STATUS === "b3" || CURRENT_STATUS === "n") {
        displayGameOverMessage(data);
    }

    if (previousSelectedPiece) {
        SELECTED_PIECE = getPieceAt(previousSelectedPiece.x, previousSelectedPiece.y);
        if (SELECTED_PIECE && SELECTED_PIECE.color === (user_color === 'w' ? 0 : 1)) {
            IS_SELECTED = true;
            server_get_possible_moves(SELECTED_PIECE, function(moves) {
                possibleMoves = moves;
            });
        } else {
            IS_SELECTED = false;
            SELECTED_PIECE = null;
            possibleMoves = [];
        }
    }

    if (data.move_history) {
        updateMovesList(data.move_history);
    }
}

function displayGameOverMessage(data) {
  let modal = document.getElementById("game-over-modal");
  let title = document.getElementById("game-over-title");
  let message = document.getElementById("game-over-message");

  let resultText = "";
  if (data.result === "win") {
    resultText = "Вы победили!";
  } else if (data.result === "lose") {
    resultText = "Вы проиграли.";
  } else if (data.result === "draw") {
    resultText = "Ничья.";
  }

  let points_gained = data.points_gained || 0;

  title.innerText = "Игра окончена";
  message.innerHTML = `
    ${resultText}<br>
    Вы получили ${points_gained} очков к рангу.
  `;

  modal.style.display = "block";
}

function returnToMainMenu() {
  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/leave_game", true);
  xhr.setRequestHeader("Content-type", "application/json");
  xhr.onreadystatechange = function() {
    if (xhr.readyState === XMLHttpRequest.DONE) {
      window.location.href = "/";
    }
  };
  xhr.send(JSON.stringify({}));
}

function give_up() {
  document.getElementById('surrender-modal').style.display = 'block';
}

function confirmSurrender() {
  closeModal('surrender-modal');

  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/give_up", true);
  xhr.setRequestHeader("Content-type", "application/json");
  xhr.onreadystatechange = function () {
    if (xhr.readyState === XMLHttpRequest.DONE) {
      if (xhr.status === 200) {
        let response = JSON.parse(xhr.responseText);
        displayGameOverMessage(response);
      } else {
        showError('Произошла ошибка при попытке сдаться.');
      }
    }
  };
  xhr.send(JSON.stringify({game_id: game_id, user_login: user_login}));
}

function give_draw() {
  document.getElementById('offer-draw-modal').style.display = 'block';
}

function confirmOfferDraw() {
  closeModal('offer-draw-modal');

  let body = {
    game_id: game_id
  };

  fetch('/offer_draw', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      showError(data.error);
    } else {
      showNotification('Предложение ничьей отправлено.');
    }
  })
  .catch(error => {
    console.error('Error:', error);
    showError('Произошла ошибка при отправке предложения ничьей.');
  });
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = 'none';
}

function showNotification(message, type = 'info') {
  let notification = document.createElement('div');
  notification.classList.add('notification');
  notification.innerText = message;

  if (type === 'error') {
    notification.classList.add('notification-error');
  } else {
    notification.classList.add('notification-info');
  }

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.classList.add('fade-out');
  }, 3000);

  notification.addEventListener('transitionend', () => {
    notification.remove();
  });
}

function showError(message) {
  let errorModal = document.createElement('div');
  errorModal.classList.add('modal');
  errorModal.innerHTML = `
      <div class="modal-content">
          <h2>Ошибка</h2>
          <p>${message}</p>
          <button onclick="this.parentElement.parentElement.style.display='none'">Закрыть</button>
      </div>
  `;
  document.body.appendChild(errorModal);
  errorModal.style.display = 'block';
}

function respond_draw(response) {
  let body = {
    game_id: game_id,
    response: response
  };

  fetch('/respond_draw', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      showError(data.error);
    } else {
      document.getElementById("draw-offer-modal").style.display = "none";
    }
  })
  .catch(error => {
    console.error('Error:', error);
    showError('Произошла ошибка при ответе на предложение ничьей.');
  });
}

// SERVER REQUEST CODE
function server_move_request(selected_piece, new_pos) {
  let data = {
    selected_piece: selected_piece,
    new_pos: new_pos,
    user_login: user_login,
    game_id: game_id,
  };

  if (user_color == "b") {
    data.selected_piece = translate([selected_piece])[0];
    data.new_pos = {
      x: 7 - new_pos.x,
      y: 7 - new_pos.y
    };
  }

  fetch('/move', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      showError(data.error);
      server_update_request(CURRENT_STATUS, pieces);
    } else {
      update_data(data);
      let movedPiece = getPieceAt(new_pos.x, new_pos.y);
      if (movedPiece && data.multiple_capture) {
        IS_SELECTED = true;
        SELECTED_PIECE = movedPiece;
        server_get_possible_moves(SELECTED_PIECE, function(moves) {
          possibleMoves = moves;
        });
      } else {
        IS_SELECTED = false;
        SELECTED_PIECE = null;
        possibleMoves = [];
      }
    }
  })
  .catch(error => {
    console.error('Error:', error);
    showError('Произошла ошибка при отправке хода.');
  });
}

function server_update_request(status, pieces) {
  let body = {
    status_: status,
    pieces: pieces,
    user_login: user_login,
    game_id: game_id,
  };

  fetch('/update_board', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  })
  .then(response => response.json())
  .then(data => {
    update_data(data);
  })
  .catch(error => {
    console.error('Error:', error);
  });
}

function server_get_possible_moves(selected_piece, callback) {
  let data = {
    selected_piece: selected_piece,
    game_id: game_id,
    user_login: user_login,
  };

  if (user_color == "b") {
    data.selected_piece = translate([selected_piece])[0];
  }

  fetch('/get_possible_moves', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(errData => Promise.reject(errData));
    }
    return response.json();
  })
  .then(data => {
    if (user_color == "b") {
      data.moves = data.moves.map(move => ({ x: 7 - move.x, y: 7 - move.y }));
    }
    callback(data.moves);
  })
  .catch(error => {
    console.error('Error:', error);
    showError(error.error || 'Произошла ошибка при получении возможных ходов.');
    IS_SELECTED = false;
    SELECTED_PIECE = null;
    possibleMoves = [];
  });
}

function startPolling() {
  setInterval(() => server_update_request(CURRENT_STATUS, pieces), 1000);
}

function applyMove(boardState, move) {
    let newState = boardState.map(piece => ({...piece}));
    let movingPiece = newState.find(p => p.x === move.from.x && p.y === move.from.y);
    if (movingPiece) {
        movingPiece.x = move.to.x;
        movingPiece.y = move.to.y;
        if (move.captured) {
            let capturedX = Math.floor((move.from.x + move.to.x) / 2);
            let capturedY = Math.floor((move.from.y + move.to.y) / 2);
            let capturedPieceIndex = newState.findIndex(p => p.x === capturedX && p.y === capturedY);
            if (capturedPieceIndex !== -1) {
                newState.splice(capturedPieceIndex, 1);
            }
        }
        if (move.promotion) {
            movingPiece.mode = 'k';
        }
    }
    return newState;
}


// CLICK HANDLING CODE
function addEventListeners() {
  CANVAS.addEventListener("click", onClick);
  window.addEventListener("resize", onResize);
}

function onClick(evt) {
    if (currentView !== null) return;
    evt.preventDefault();

    let loc = {
        x: evt.offsetX,
        y: evt.offsetY,
    };
    let coords = getCoordinates(loc);
    if (coords.x === -1 || coords.y === -1) return;

    if (!IS_SELECTED) {
        SELECTED_PIECE = getPieceAt(coords.x, coords.y);
        if (SELECTED_PIECE && SELECTED_PIECE.color === (user_color === 'w' ? 0 : 1)) {
            IS_SELECTED = true;
            server_get_possible_moves(SELECTED_PIECE, function(moves) {
                possibleMoves = moves;
            });
        }
    } else {
        let move = possibleMoves.find(m => m.x === coords.x && m.y === coords.y);
        if (move) {
            server_move_request(SELECTED_PIECE, move);
        } else {
            IS_SELECTED = false;
            SELECTED_PIECE = null;
            possibleMoves = [];
        }
    }
}

function onResize() {
    adjustScreen();
}

function getPieceAt(x, y) {
  for (let piece of pieces) {
    if (piece.x === x && piece.y === y) {
      return piece;
    }
  }
  return null;
}

// RENDER CODE
function adjustScreen() {
  const screenWidth = window.innerWidth;
  const screenHeight = window.innerHeight;
  let size;

  if (screenWidth <= 1024) {
    size = Math.min(screenWidth * 0.65, screenHeight * 0.65);
    LABEL_PADDING = 30;
  } else if (screenWidth <= 1440) {
    size = Math.min(screenWidth * 0.9, screenHeight * 0.8);
    LABEL_PADDING = 36;
  } else {
    size = Math.min(screenWidth * 0.95, screenHeight * 0.8);
    LABEL_PADDING = 36;
  }

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

function draw_circle(x, y, r, width, strokeColor, fillColor) {
  CTX.beginPath();
  CTX.arc(x, y, r, 0, 2 * Math.PI, false);
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
  const X = BOARD_OFFSET_X + CELL_SIZE * (piece.x + 0.5);
  const Y = BOARD_OFFSET_Y + CELL_SIZE * (piece.y + 0.5);
  const radius = (CELL_SIZE / 2) * 0.8;

  const innerRadius = radius * 0.7;
  const crownRadius = radius * 0.5;

  draw_circle(X, Y, radius, 3, strokeStyle, fillStyle);
  draw_circle(X, Y, innerRadius, 3, strokeStyle, false);

  if (piece.mode !== "p") {
    CTX.beginPath();
    CTX.arc(X, Y, crownRadius, 0, 2 * Math.PI, false);
    CTX.fillStyle = "rgba(255, 215, 0, 0.7)";
    CTX.fill();
    CTX.lineWidth = 6;
    CTX.strokeStyle = "gold";
    CTX.stroke();
    CTX.closePath();
  }

  if (IS_SELECTED && SELECTED_PIECE === piece) {
    CTX.save();
    CTX.shadowColor = 'rgba(255, 255, 0, 1)';
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

function draw_possible_moves() {
  CTX.save();
  CTX.lineWidth = 4;
  CTX.strokeStyle = 'rgba(0, 162, 255, 0.8)';
  CTX.shadowColor = 'rgba(0, 162, 255, 0.8)';
  CTX.shadowBlur = 10;
  for (let move of possibleMoves) {
    const X = BOARD_OFFSET_X + CELL_SIZE * move.x;
    const Y = BOARD_OFFSET_Y + CELL_SIZE * move.y;
    CTX.strokeRect(X, Y, CELL_SIZE, CELL_SIZE);
  }
  CTX.restore();
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

function drawLabels() {
  CTX.fillStyle = "#f0f0f0";
  CTX.font = `${CELL_SIZE / 3}px Arial`;
  CTX.textAlign = "center";
  CTX.textBaseline = "middle";

  const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

  for (let i = 0; i < 8; i++) {
    const x = BOARD_OFFSET_X + CELL_SIZE * i + CELL_SIZE / 2;
    const y = BOARD_OFFSET_Y - LABEL_PADDING / 2;
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
    CTX.fillText(i + 1, x, y);
  }

  for (let i = 0; i < 8; i++) {
    const x = BOARD_OFFSET_X + CELL_SIZE * 8 + LABEL_PADDING / 2;
    const y = BOARD_OFFSET_Y + CELL_SIZE * (7 - i) + CELL_SIZE / 2;
    CTX.fillText(i + 1, x, y);
  }
}

function render_Pieces() {
  for (let i = 0; i < pieces.length; i++) {
    draw_piece(pieces[i], user_color);
  }
  if (IS_SELECTED) {
    draw_possible_moves();
  }
}

function update() {
  CTX.clearRect(0, 0, CANVAS.width / (window.devicePixelRatio || 1), CANVAS.height / (window.devicePixelRatio || 1));
  render_Board();
  render_Pieces();
  window.requestAnimationFrame(update);
}

// CLICK HANDLING CODE

function convertCoordinatesToNotation(x, y) {
  const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
  if (user_color == 'w') {
    let file = letters[x];
    let rank = 8 - y;
    return file + rank;
  } else {
    let file = letters[7 - x];
    let rank = y + 1;
    return file + rank;
  }
}

function updateMovesList(moveHistory) {
    const movesList = document.querySelector('.moves-list');
    const movesContainer = document.querySelector('.moves-container');

    let hasNewMoves = moveHistory.length > lastMoveCount;

    for (let i = lastMoveCount; i < moveHistory.length; i++) {
        let move = {...moveHistory[i]};
        if (user_color == "b") {
            move.from = {x: 7 - move.from.x, y: 7 - move.from.y};
            move.to = {x: 7 - move.to.x, y: 7 - move.to.y};
        }

        let isPlayerMove = move.player === user_login;
        let player = isPlayerMove ? `<span class="player-name blue" data-username="${user_login}">${user_login}</span>` : `<span class="player-name red" data-username="${opponent_login}">${opponent_login}</span>`;
        let fromPos = convertCoordinatesToNotation(move.from.x, move.from.y);
        let toPos = convertCoordinatesToNotation(move.to.x, move.to.y);
        let moveText = `${fromPos} ${move.captured ? 'x' : '-'} ${toPos}`;

        let li = document.createElement('li');
        li.classList.add(isPlayerMove ? 'player-move' : 'opponent-move', 'new-move');

        let moveContent = document.createElement('div');
        moveContent.classList.add('move-content');

        let playerLabel = document.createElement('span');
        playerLabel.classList.add('move-player');
        playerLabel.innerHTML = player;

        let moveDescription = document.createElement('span');
        moveDescription.classList.add('move-description');
        moveDescription.textContent = moveText;

        moveContent.appendChild(playerLabel);
        moveContent.appendChild(moveDescription);
        li.appendChild(moveContent);

        li.addEventListener('click', () => {
            document.querySelectorAll('.moves-list li').forEach(moveLi => moveLi.classList.remove('selected'));
            li.classList.add('selected');
            viewBoardState(i + 1);
        });

        li.addEventListener('animationend', () => {
            li.classList.remove('new-move');
        });

        movesList.appendChild(li);

        let lastState = boardStates[boardStates.length - 1];
        let newState = applyMove(lastState, move);
        boardStates.push(newState);
    }

    lastMoveCount = moveHistory.length;

    if (hasNewMoves) {
        movesContainer.scrollTop = movesContainer.scrollHeight;
    }

    addProfileClickListeners();
}

function viewBoardState(moveIndex) {
    if (moveIndex < 0 || moveIndex > boardStates.length - 1) return;
    pieces = boardStates[moveIndex].map(piece => ({...piece}));
    currentView = moveIndex;
    showHistoryViewIndicator();
}

function returnToCurrentView() {
    pieces = boardStates[boardStates.length - 1].map(piece => ({...piece}));
    currentView = null;
    let indicator = document.getElementById('history-view-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }

    document.querySelectorAll('.moves-list li').forEach(moveLi => moveLi.classList.remove('selected'));
}

function showHistoryViewIndicator() {
    let indicator = document.getElementById('history-view-indicator');
    if (!indicator) return;
    indicator.style.display = 'block';
}

function addProfileClickListeners() {
    const playerNames = document.querySelectorAll('.player-name');
    playerNames.forEach(name => {
        name.addEventListener('click', (event) => {
            event.stopPropagation();
            const username = name.getAttribute('data-username');

            const movesContainer = document.querySelector('.moves-container');
            const movesRect = movesContainer.getBoundingClientRect();

            const rect = name.getBoundingClientRect();

            const x = movesRect.left + window.scrollX;
            const y = rect.top + window.scrollY;

            showContextMenu(x, y, username);
        });
    });
}

function showContextMenu(x, y, username) {
    const menu = document.getElementById('context-menu');
    if (!menu) return;

    menu.style.top = `${y}px`;
    menu.style.left = `${x}px`;
    menu.style.display = 'block';

    menu.querySelector('#view-stats').onclick = null;
    menu.querySelector('#go-to-profile').onclick = null;

    menu.querySelector('#view-stats').addEventListener('click', () => {
        fetchProfile(username);
        menu.style.display = 'none';
    });

    menu.querySelector('#go-to-profile').addEventListener('click', () => {
        window.location.href = `/profile/${username}`;
        menu.style.display = 'none';
    });
}


function createContextMenu() {
    let menu = document.createElement('div');
    menu.id = 'context-menu';
    menu.classList.add('context-menu');
    menu.innerHTML = `
        <ul>
            <li id="view-stats">Просмотреть статистику</li>
            <li id="go-to-profile">Перейти в профиль</li>
        </ul>
    `;
    document.body.appendChild(menu);

    document.addEventListener('click', function(event) {
        if (!menu.contains(event.target)) {
            menu.style.display = 'none';
        }
    });

    menu.addEventListener('click', function(event) {
        event.stopPropagation();
    });
}

createContextMenu();

function fetchProfile(username) {
    fetch(`/api/profile/${username}`)
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
        } else {
            displayProfileModal(data);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Произошла ошибка при загрузке профиля.');
    });
}

function displayProfileModal(profileData) {
    let modal = document.getElementById("profile-modal");
    if (!modal) {
        modal = document.createElement('div');
        modal.id = "profile-modal";
        modal.classList.add('modal');
        modal.innerHTML = `
            <div class="modal-content">
                <h2>Профиль игрока</h2>
                <p><strong>Имя пользователя:</strong> <span id="profile-username"></span></p>
                <p><strong>Рейтинг:</strong> <span id="profile-rang"></span></p>
                <p><strong>Игр сыграно:</strong> <span id="profile-total-games"></span></p>
                <p><strong>Победы:</strong> <span id="profile-wins"></span></p>
                <p><strong>Ничьих:</strong> <span id="profile-draws"></span></p>
                <p><strong>Поражения:</strong> <span id="profile-losses"></span></p>
                <button onclick="closeModal('profile-modal')">Закрыть</button>
            </div>
        `;
        document.body.appendChild(modal);
    }

    document.getElementById('profile-username').textContent = profileData.user_login;
    document.getElementById('profile-rang').textContent = profileData.rang;
    document.getElementById('profile-total-games').textContent = profileData.total_games;
    document.getElementById('profile-wins').textContent = profileData.wins;
    document.getElementById('profile-draws').textContent = profileData.draws;
    document.getElementById('profile-losses').textContent = profileData.losses;

    modal.style.display = 'block';
}

// SERVER REQUEST CODE

function startPolling() {
  setInterval(() => server_update_request(CURRENT_STATUS, pieces), 1000);
}

// SERVER REQUEST CODE
function onLoad() {
    CANVAS = document.getElementById("board");
    CTX = CANVAS.getContext("2d");
    HEADER_HEIGHT = document.getElementsByClassName("header")[0].clientHeight;
    if (user_color == "b") {
        pieces = translate(pieces);
    }
    boardStates = [JSON.parse(JSON.stringify(pieces))];
    adjustScreen();
    update();
    addEventListeners();
    startPolling();
}


// CLICK HANDLING CODE

// RENDER CODE END

function getCoordinates(loc) {
  let gridX = Math.floor((loc.x - BOARD_OFFSET_X) / CELL_SIZE);
  let gridY = Math.floor((loc.y - BOARD_OFFSET_Y) / CELL_SIZE);

  if (
    gridX >= 0 &&
    gridX < 8 &&
    gridY >= 0 &&
    gridY < 8 &&
    (gridX + gridY) % 2 === 1
  ) {
    return { x: gridX, y: gridY };
  }
  return { x: -1, y: -1 };
}

// MOVE LIST
