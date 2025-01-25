let CANVAS = null;
let CTX = null;
let SELECTED_PIECE = null;
let IS_SELECTED = false;
let CELL_SIZE = 0;
let BOARD_OFFSET_X = 0;
let BOARD_OFFSET_Y = 0;
let CURRENT_STATUS = "w1";
let LABEL_PADDING = 36;
let lastMoveCount = 0;
let boardStates = [];
let currentView = null;
let gameFoundSoundPlayed = false;
let victorySoundPlayed = false;
let defeatSoundPlayed = false;
let gameOverShown = false;
let shownErrors = new Set();

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
  ns1: "Игра не началась из-за отсутствия хода",
  e1: "Ошибка при запросе к серверу"
};

let colors = {
  1: "rgb(0, 0, 0)",
  0: "rgb(255, 255, 255)"
};

let b_colors = {
  1: "#971616",
  0: "#971616"
};

let pieces = [];
let possibleMoves = [];

function translate(pieces_data) {
  return pieces_data.map(piece => ({
    color: piece.color,
    x: 7 - piece.x,
    y: 7 - piece.y,
    mode: piece.mode,
    is_king: piece.is_king
  }));
}

function update_data(data) {
  if (data.error) {
    if (data.error === "Game over") {
      displayGameOverMessage(data);
      return;
    }
    showError(data.error);
    if (data.error === "Invalid game ID") {
      alert("Произошла ошибка: " + data.error);
    }
    return;
  }
  CURRENT_STATUS = data.status_;
  if (data.white_time !== undefined && data.black_time !== undefined) {
    updateTimersDisplay(data.white_time, data.black_time);
  }
  if (data.white_countdown !== undefined && data.black_countdown !== undefined) {
    updateCountdownDisplay(data.white_countdown, data.black_countdown);
  }
  let previousSelectedPiece = SELECTED_PIECE ? { ...SELECTED_PIECE } : null;
  if (currentView === null) {
    if (data.pieces) {
      pieces = data.pieces;
      if (user_color === "b") pieces = translate(pieces);
      if (pieces && pieces.length > 0 && boardStates.length === 0) {
        boardStates = [JSON.parse(JSON.stringify(pieces))];
      }
    } else {
      console.error("data.pieces is undefined");
      showError("Получены некорректные данные от сервера.");
      return;
    }
  }
  document.getElementById("status").innerHTML = status[CURRENT_STATUS];
  if (!gameFoundSoundPlayed && (CURRENT_STATUS === "w1" || CURRENT_STATUS === "b1")) {
    let gameFoundSound = document.getElementById('sound-game-found');
    if (gameFoundSound) {
      gameFoundSound.play().catch(() => {});
      gameFoundSoundPlayed = true;
    }
  }
  if (data.draw_response) {
    if (data.draw_response === 'accept') {
      displayGameOverMessage(data);
    } else if (data.draw_response === 'decline') {
      showNotification('Ваше предложение ничьей было отклонено.', 'error');
    }
  }
  if (data.draw_offer) {
    if (data.draw_offer !== user_color) {
      let modal = document.getElementById("draw-offer-modal");
      modal.style.display = "block";
    }
  } else {
    document.getElementById("draw-offer-modal").style.display = "none";
  }
  if (CURRENT_STATUS === "w3" || CURRENT_STATUS === "b3" || CURRENT_STATUS === "n" || CURRENT_STATUS === "ns1") {
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

function updateTimersDisplay(whiteSeconds, blackSeconds) {
  function formatTime(s) {
    let m = Math.floor(s / 60);
    let sec = Math.floor(s % 60);
    let mm = m < 10 ? '0' + m : m;
    let ss = sec < 10 ? '0' + sec : sec;
    return mm + ':' + ss;
  }
  document.getElementById('white-timer').textContent = formatTime(whiteSeconds);
  document.getElementById('black-timer').textContent = formatTime(blackSeconds);
}

function updateCountdownDisplay(wCountdown, bCountdown) {
  const whiteTimer = document.getElementById('white-timer');
  const blackTimer = document.getElementById('black-timer');
  if (wCountdown > 0 &&
      CURRENT_STATUS !== 'ns1' &&
      CURRENT_STATUS !== 'w3' &&
      CURRENT_STATUS !== 'b3' &&
      CURRENT_STATUS !== 'n') {
    let m = Math.floor(wCountdown / 60);
    let s = Math.floor(wCountdown % 60);
    let mm = m < 10 ? '0' + m : m;
    let ss = s < 10 ? '0' + s : s;
    whiteTimer.textContent = mm + ':' + ss;
    if (Math.floor(wCountdown) % 2 === 0) {
      whiteTimer.style.color = '#FF0000';
    } else {
      whiteTimer.style.color = '#FFFFFF';
    }
  } else {
    whiteTimer.style.color = '#FFFFFF';
  }
  if (bCountdown > 0 &&
      CURRENT_STATUS !== 'ns1' &&
      CURRENT_STATUS !== 'w3' &&
      CURRENT_STATUS !== 'b3' &&
      CURRENT_STATUS !== 'n') {
    let m = Math.floor(bCountdown / 60);
    let s = Math.floor(bCountdown % 60);
    let mm = m < 10 ? '0' + m : m;
    let ss = s < 10 ? '0' + s : s;
    blackTimer.textContent = mm + ':' + ss;
    if (Math.floor(bCountdown) % 2 === 0) {
      blackTimer.style.color = '#FF0000';
    } else {
      blackTimer.style.color = '#FFFFFF';
    }
  } else {
    blackTimer.style.color = '#FFFFFF';
  }
}

function displayGameOverMessage(data) {
    if (gameOverShown) return;
    gameOverShown = true;
    let modal = document.getElementById("game-over-modal");
    if (modal.style.display === "block") return;
    let title = document.getElementById("game-over-title");
    let message = document.getElementById("game-over-message");
    let resultText = "";
    let isVictory = false;
    let isDefeat = false;
    let gameResult = data.result;
    if (!gameResult) {
        if (CURRENT_STATUS === 'w3') {
            gameResult = (user_color === 'w') ? 'win' : 'lose';
        } else if (CURRENT_STATUS === 'b3') {
            gameResult = (user_color === 'b') ? 'win' : 'lose';
        } else if (CURRENT_STATUS === 'n') {
            gameResult = 'draw';
        } else if (CURRENT_STATUS === 'ns1') {
            gameResult = 'not_started';
        }
    }
    let userIsGhost = is_ghost;
    let opponentIsGhost = opponent_login.startsWith('ghost');
    if (userIsGhost) {
        resultText = "Вы не получаете очки, пока не зарегистрированы.";
    } else {
        if (gameResult === "win") {
            resultText = "Вы победили!";
            isVictory = true;
        } else if (gameResult === "lose") {
            resultText = "Вы проиграли.";
            isDefeat = true;
        } else if (gameResult === "draw") {
            resultText = "Ничья.";
        } else if (gameResult === "not_started") {
            resultText = "Игра не началась из-за отсутствия хода.";
        }
    }
    let points_gained = data.points_gained || 0;
    title.innerText = "Игра окончена";
    if (userIsGhost) {
        message.innerHTML = resultText;
    } else {
        message.innerHTML = resultText + "<br>Вы получили " + points_gained + " очков к рангу.";
    }
    const modalButtons = modal.querySelector('.modal-buttons');
    const registerButton = document.getElementById('register-button');
    if (userIsGhost) {
        registerButton.style.display = 'inline-block';
        modalButtons.classList.add('two-buttons');
        modalButtons.classList.remove('single-button');
    } else {
        registerButton.style.display = 'none';
        modalButtons.classList.remove('two-buttons');
        modalButtons.classList.add('single-button');
    }
    const modalContent = modal.querySelector('.modal-content');
    if (userIsGhost) {
        modalContent.classList.add('guest');
        modalContent.classList.remove('registered');
    } else {
        modalContent.classList.remove('guest');
        modalContent.classList.add('registered');
    }
    modal.style.display = "block";
    if (isVictory && !victorySoundPlayed) {
        playVictorySound();
        victorySoundPlayed = true;
    } else if (isDefeat && !defeatSoundPlayed) {
        playDefeatSound();
        defeatSoundPlayed = true;
    }
}

function returnToMainMenu() {
  const xhr = new XMLHttpRequest();
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
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/give_up", true);
  xhr.setRequestHeader("Content-type", "application/json");
  xhr.onreadystatechange = function() {
    if (xhr.readyState === XMLHttpRequest.DONE) {
      if (xhr.status === 200) {
        const response = JSON.parse(xhr.responseText);
        displayGameOverMessage(response);
      } else {
        showError('Произошла ошибка при попытке сдаться.');
      }
    }
  };
  xhr.send(JSON.stringify({ game_id: game_id, user_login: user_login }));
}

function give_draw() {
  document.getElementById('offer-draw-modal').style.display = 'block';
}

function confirmOfferDraw() {
  closeModal('offer-draw-modal');
  let body = { game_id: game_id };
  fetch('/offer_draw', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
    .catch(() => {
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
  if (shownErrors.has(message)) return;
  shownErrors.add(message);
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
  let body = { game_id: game_id, response: response };
  fetch('/respond_draw', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
    .catch(() => {
      showError('Произошла ошибка при ответе на предложение ничьей.');
    });
}

function server_move_request(selected_piece, new_pos) {
  let data = {
    selected_piece: selected_piece,
    new_pos: new_pos,
    game_id: game_id
  };
  if (user_color === "b") {
    if (selected_piece) {
      data.selected_piece = translate([selected_piece])[0];
      data.new_pos = { x: 7 - new_pos.x, y: 7 - new_pos.y };
    } else {
      showError('Выбранная фигура не существует.');
      return;
    }
  }
  fetch('/move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        showError(data.error);
      } else {
        update_data(data);
        playMoveSound();
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
    .catch(() => {
      showError('Произошла ошибка при отправке хода.');
    });
}

let isUpdating = false;

function server_update_request() {
  if (gameOverShown) return Promise.resolve();
  if (isUpdating) return Promise.resolve();
  if (!game_id) {
    console.error("game_id не определён.");
    return Promise.reject("game_id не определён.");
  }

  isUpdating = true;
  let body = { game_id: game_id };

  return fetch('/update_board', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
    .then(response => {
      if (!response.ok) {
        if (response.status === 404) {
          return { error: "Game over" };
        }
        return response.json().then(errData => Promise.reject(errData));
      }
      return response.json();
    })
    .then(data => {
      if (data.error) {
        if (data.error === "Game over") {
          displayGameOverMessage(data);
          return Promise.resolve();
        }
        if (!gameOverShown) {
          showError(data.error);
        }
        return Promise.reject(data.error);
      } else {
        const newBoardHash = JSON.stringify(data.pieces);
        const currentBoardHash = JSON.stringify(pieces);

        if (newBoardHash !== currentBoardHash) {
          console.log("Обнаружено обновление состояния доски.");
          pieces = data.pieces;
          boardStates.push(data.pieces);
          update_data(data);
        } else {
          console.log("Состояние доски не изменилось.");
        }

        return Promise.resolve();
      }
    })
    .catch(error => {
      if (typeof error === "string" && error === "Game over") {
        displayGameOverMessage({ error: "Game over" });
        return Promise.resolve();
      }
      console.error("Ошибка при обновлении доски:", error);
      return Promise.reject(error);
    })
    .finally(() => {
      isUpdating = false;
    });
}


function server_get_possible_moves(selected_piece, callback) {
  let data = {
    selected_piece: selected_piece,
    game_id: game_id,
    user_login: user_login
  };
  if (user_color === "b") {
    if (selected_piece) {
      data.selected_piece = translate([selected_piece])[0];
    } else {
      showError('Выбранная фигура не существует.');
      return;
    }
  }
  fetch('/get_possible_moves', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
    .then(response => {
      if (!response.ok) {
        return response.json().then(errData => Promise.reject(errData));
      }
      return response.json();
    })
    .then(data => {
      if (data.error) {
        showError(data.error);
        return;
      }
      if (user_color === "b") {
        data.moves = data.moves.map(move => ({ x: 7 - move.x, y: 7 - move.y }));
      }
      callback(data.moves);
    })
    .catch(() => {
      showError('Произошла ошибка при получении возможных ходов.');
      IS_SELECTED = false;
      SELECTED_PIECE = null;
      possibleMoves = [];
    });
}

function applyMove(boardState, move) {
  let newState = boardState.map(piece => ({ ...piece }));
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

function addEventListeners() {
  CANVAS.addEventListener("click", onClick);
  window.addEventListener("resize", onResize);
}

function onClick(evt) {
  if (currentView !== null) return;
  evt.preventDefault();
  let loc = { x: evt.offsetX, y: evt.offsetY };
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

function adjustScreen() {
  const screenWidth = window.innerWidth;
  const screenHeight = window.innerHeight;
  let size;
  if (screenWidth <= 1024) {
    size = Math.min(screenWidth * 0.65, screenHeight * 0.65);
    LABEL_PADDING = 30;
  } else if (screenWidth <= 1440) {
    size = Math.min(screenWidth * 0.75, screenHeight * 0.75);
    LABEL_PADDING = 36;
  } else {
    size = Math.min(screenWidth * 0.75, screenHeight * 0.75);
    LABEL_PADDING = 36;
  }
  size = Math.max(300, Math.min(size, 800));
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
  let fontSize = CELL_SIZE / 3;
  fontSize = Math.max(12, Math.min(fontSize, 24));
  CTX.font = fontSize + "px Arial";
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
    CTX.fillText((i + 1).toString(), x, y);
  }
  for (let i = 0; i < 8; i++) {
    const x = BOARD_OFFSET_X + CELL_SIZE * 8 + LABEL_PADDING / 2;
    const y = BOARD_OFFSET_Y + CELL_SIZE * (7 - i) + CELL_SIZE / 2;
    CTX.fillText((i + 1).toString(), x, y);
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
  CTX.clearRect(
    0,
    0,
    CANVAS.width / (window.devicePixelRatio || 1),
    CANVAS.height / (window.devicePixelRatio || 1)
  );
  render_Board();
  render_Pieces();
  window.requestAnimationFrame(update);
}

function convertCoordinatesToNotation(x, y) {
  const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
  if (user_color === 'w') {
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
    let move = { ...moveHistory[i] };
    let isPlayerMove = move.player === user_login;
    let isGhost = isPlayerMove ? user_login.startsWith('ghost') : opponent_login.startsWith('ghost');
    let playerClass = isPlayerMove ? 'blue' : 'red';
    let playerNameClass = isGhost ? 'ghost-player' : '';
    let playerName = isPlayerMove ? user_login : opponent_login;
    let crown = '';
    if (playerName === 'WertRar') {
      crown = ' <span class="crown" title="Лучший игрок">👑</span>';
    }
    let avatarUrl = isPlayerMove ? user_avatar_url : opponent_avatar_url;
    let player = `
      <img class="move-avatar" src="${avatarUrl}" alt="avatar">
      <span class="player-name ${playerClass} ${playerNameClass}" data-username="${playerName}">
        ${playerName}${crown}
      </span>
    `;
    let fromPos = convertCoordinatesToNotation(move.from.x, move.from.y);
    let toPos = convertCoordinatesToNotation(move.to.x, move.to.y);
    let moveText = fromPos + (move.captured ? ' x ' : ' - ') + toPos;
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
    if (user_color === 'b') {
      let originalFromX = move.from.x;
      let originalFromY = move.from.y;
      move.from.x = 7 - originalFromX;
      move.from.y = 7 - originalFromY;
      let originalToX = move.to.x;
      let originalToY = move.to.y;
      move.to.x = 7 - originalToX;
      move.to.y = 7 - originalToY;
    }
    let lastState = boardStates[boardStates.length - 1];
    let newState = applyMove(lastState, move);
    boardStates.push(newState);
  }
  lastMoveCount = moveHistory.length;
  if (hasNewMoves) {
    playMoveSound();
    movesContainer.scrollTop = movesContainer.scrollHeight;
  }
  addProfileClickListeners();
}

function viewBoardState(moveIndex) {
  if (moveIndex < 0 || moveIndex > boardStates.length - 1) return;
  pieces = boardStates[moveIndex].map(piece => ({ ...piece }));
  currentView = moveIndex;
  showHistoryViewIndicator();
}

function returnToCurrentView() {
  pieces = boardStates[boardStates.length - 1].map(piece => ({ ...piece }));
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
    const username = name.getAttribute('data-username');
    if (username && !username.startsWith('ghost')) {
      name.addEventListener('click', (event) => {
        event.stopPropagation();
        const movesContainer = document.querySelector('.moves-container');
        const movesRect = movesContainer.getBoundingClientRect();
        const rect = name.getBoundingClientRect();
        const x = movesRect.left + window.scrollX;
        const y = rect.top + window.scrollY;
        showContextMenu(x, y, username);
      });
    }
  });
}

function showContextMenu(x, y, username) {
  const menu = document.getElementById('context-menu');
  if (!menu) return;
  menu.style.top = y + 'px';
  menu.style.left = x + 'px';
  menu.style.display = 'block';
  menu.querySelector('#view-stats').onclick = null;
  menu.querySelector('#go-to-profile').onclick = null;
  menu.querySelector('#view-stats').addEventListener('click', () => {
    fetchProfile(username);
    menu.style.display = 'none';
  });
  menu.querySelector('#go-to-profile').addEventListener('click', () => {
    window.location.href = '/profile/' + username;
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
  fetch('/api/profile/' + username)
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        showError(data.error);
      } else {
        displayProfileModal(data);
      }
    })
    .catch(() => {
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
  let crown = '';
  if (profileData.user_login === 'WertRar') {
    crown = ' <span class="crown" title="Лучший игрок">👑</span>';
  }
  document.getElementById('profile-username').innerHTML = profileData.user_login + crown;
  document.getElementById('profile-rang').textContent = profileData.rang;
  document.getElementById('profile-total-games').textContent = profileData.total_games;
  document.getElementById('profile-wins').textContent = profileData.wins;
  document.getElementById('profile-draws').textContent = profileData.draws;
  document.getElementById('profile-losses').textContent = profileData.losses;
  modal.style.display = 'block';
}

function checkGameStatus() {
  fetch('/check_game_status', {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'game_not_found') {
        window.location.href = "/";
      }
    })
    .catch(() => {});
}

let pollingInterval = 1000;

function startPolling() {
  setInterval(() => {
    server_update_request()
      .then(() => {
        pollingInterval = 1000;
      })
      .catch(() => {
        pollingInterval = Math.min(pollingInterval * 2, 60000);
      });
  }, pollingInterval);
  if (game_id && user_login) {
    setInterval(checkGameStatus, 5000);
  }
}

function onLoad() {
  CANVAS = document.getElementById("board");
  CTX = CANVAS.getContext("2d");
  CTX.imageSmoothingEnabled = true;
  let HEADER_HEIGHT = document.getElementsByClassName("header")[0].clientHeight;
  adjustScreen();
  server_update_request().then(() => {
    update();
    addEventListeners();
    startPolling();
    let gameFoundSound = document.getElementById('sound-game-found');
    if (gameFoundSound) {
      gameFoundSound.volume = 0.35;
      gameFoundSound.play().catch(() => {});
    }
    if (user_login.startsWith('ghost')) {
      disableProfileFeatures();
    }
    notify_player_loaded();
  });
}

function disableProfileFeatures() {
  const ghostPlayers = document.querySelectorAll('.player-name[data-username^="ghost"]');
  ghostPlayers.forEach(button => {
    button.style.cursor = 'default';
    button.style.opacity = '0.6';
    button.style.userSelect = 'none';
  });
}

function getCoordinates(loc) {
  let gridX = Math.floor((loc.x - BOARD_OFFSET_X) / CELL_SIZE);
  let gridY = Math.floor((loc.y - BOARD_OFFSET_Y) / CELL_SIZE);
  if (gridX >= 0 && gridX < 8 && gridY >= 0 && gridY < 8 && (gridX + gridY) % 2 === 1) {
    return { x: gridX, y: gridY };
  }
  return { x: -1, y: -1 };
}

function playMoveSound() {
  const moveSound = document.getElementById('sound-move');
  if (moveSound) {
    moveSound.volume = 0.3;
    moveSound.currentTime = 0;
    moveSound.play().catch(() => {});
  }
}

function playVictorySound() {
  const victorySound = document.getElementById('sound-victory');
  if (victorySound) {
    victorySound.volume = 0.35;
    victorySound.currentTime = 0;
    victorySound.play().catch(() => {});
  }
}

function playDefeatSound() {
  const defeatSound = document.getElementById('sound-defeat');
  if (defeatSound) {
    defeatSound.volume = 0.35;
    defeatSound.currentTime = 0;
    defeatSound.play().catch(() => {});
  }
}

function notify_player_loaded() {
  if (typeof game_id === 'undefined' || typeof user_login === 'undefined') {
    return;
  }
  fetch('/player_loaded', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ game_id: game_id, user_login: user_login })
  })
    .then(() => {})
    .catch(() => {});
}

window.addEventListener('load', onLoad);
