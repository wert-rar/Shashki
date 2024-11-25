
let CANVAS = null;
let CTX = null;
let SELECTED_PIECE = null;
let IS_SELECTED = false;
let CELL_SIZE = 0;
let BOARD_OFFSET_X = 0;
let BOARD_OFFSET_Y = 0;
let CURRENT_STATUS = "w1";
let SERVER_IP = "";

console.log(user_color);
console.log(user_login, game_id);

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
  1: "#2E2E2E",
  0: "#1C1C1C",
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


function translate(pieces_data) {
  let n_pieces = [];
  for (let i = 0; i < pieces_data.length; i++) {
    n_pieces.push({
      color: pieces_data[i].color,
      x: 7 - pieces_data[i].x,
      y: 7 - pieces_data[i].y,
      mode: pieces_data[i].mode,
    });
  }
  return n_pieces;
}

function update_data(data) {
  CURRENT_STATUS = data.status_;
  pieces = data.pieces;
  if (user_color == "b") pieces = translate(pieces);
  document.getElementById("status").innerHTML = status[CURRENT_STATUS];

  if (CURRENT_STATUS === "w3" || CURRENT_STATUS === "b3" || CURRENT_STATUS === "n") {
    displayGameOverMessage(data);
  }

  update();
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
  if (confirm("Вы уверены, что хотите сдаться? Это будет считаться поражением.")) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/give_up", true);
    xhr.setRequestHeader("Content-type", "application/json");
    xhr.onreadystatechange = function () {
      if (xhr.readyState === XMLHttpRequest.DONE) {
        if (xhr.status === 200) {
          let response = JSON.parse(xhr.responseText);
          displayGameOverMessage(response);
        } else {
          alert("Произошла ошибка при попытке сдаться.");
        }
      }
    };
    xhr.send(JSON.stringify({game_id: game_id, user_login: user_login}));
  }
}

// SERVER REQUEST CODE
function server_move_request(status, pieces) {
  if (user_color == "b") {
    pieces = translate(pieces);
  }
  let body = {
    status_: status,
    pieces: pieces,
    user_login: user_login,
    game_id: game_id,
  };

  let xhr = new XMLHttpRequest();
  xhr.open("POST", "/move");
  xhr.addEventListener("load", function () {
    if (xhr.status === 200 && xhr.readyState === 4) {
      let response = JSON.parse(xhr.responseText);
      update_data(response);
    } else {
      let response = JSON.parse(xhr.responseText);
      update_data({
        status_: "e1",
        pieces: pieces,
      });
      throw new Error(response.error);
    }
  });
  xhr.setRequestHeader("Content-type", "application/json");
  xhr.send(JSON.stringify(body));
}

function server_update_request(status, pieces) {
  let body =
    user_color == "b"
      ? {
          status_: status,
          pieces: translate(pieces),
          user_login: user_login,
          game_id: game_id,
        }
      : {
          status_: status,
          pieces: pieces,
          user_login: user_login,
          game_id: game_id,
        };
  if (IS_SELECTED) return;

  let xhr = new XMLHttpRequest();
  xhr.open("POST", "/update_board");
  xhr.addEventListener("load", function () {
    if (xhr.status === 200 && xhr.readyState === 4) {
      let response = JSON.parse(xhr.responseText);
      update_data(response);
    } else {
      let response = JSON.parse(xhr.responseText);
      update_data({
        status_: "e1",
        pieces: pieces,
      });
      throw new Error(response.error);
    }
  });
  xhr.setRequestHeader("Content-type", "application/json");
  xhr.send(JSON.stringify(body));
}

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
  adjustScreen();
  update();
  addEventListeners();
  startPolling();
}

// DRAG AND DROP CODE
function addEventListeners() {
  CANVAS.addEventListener("mousedown", onMouseDown);
  CANVAS.addEventListener("mousemove", onMouseMove);
  CANVAS.addEventListener("mouseup", onMouseUp);
  CANVAS.addEventListener("touchstart", onTouchStart);
  CANVAS.addEventListener("touchmove", onTouchMove);
  CANVAS.addEventListener("touchend", onTouchEnd);
  window.addEventListener("resize", adjustScreen);
}

function onMouseDown(evt) {
  evt.preventDefault();
  let rect = CANVAS.getBoundingClientRect();
  let loc = {
    x: evt.clientX - rect.left,
    y: evt.clientY - rect.top,
  };
  SELECTED_PIECE = getPressedPiece(loc);
  if (SELECTED_PIECE) {
    SELECTED_PIECE.offsetX =
      loc.x - (BOARD_OFFSET_X + CELL_SIZE * (SELECTED_PIECE.piece.x + 0.5));
    SELECTED_PIECE.offsetY =
      loc.y - (BOARD_OFFSET_Y + CELL_SIZE * (SELECTED_PIECE.piece.y + 0.5));
    IS_SELECTED = true;
  }
}

function onMouseMove(evt) {
  evt.preventDefault();
  if (SELECTED_PIECE != null && IS_SELECTED) {
    let rect = CANVAS.getBoundingClientRect();
    SELECTED_PIECE.x = evt.clientX - rect.left - SELECTED_PIECE.offsetX;
    SELECTED_PIECE.y = evt.clientY - rect.top - SELECTED_PIECE.offsetY;
  }
}

function onMouseUp(evt) {
  evt.preventDefault();
  if (SELECTED_PIECE != null) {
    let rect = CANVAS.getBoundingClientRect();
    let loc = {
      x: evt.clientX - rect.left,
      y: evt.clientY - rect.top,
    };
    let coords = getCoordinates(loc);

    if (coords.x !== -1 && coords.y !== -1) {
      SELECTED_PIECE.piece.x = coords.x;
      SELECTED_PIECE.piece.y = coords.y;

      server_move_request(CURRENT_STATUS, pieces);
    }

    SELECTED_PIECE = null;
    IS_SELECTED = false;
  }
}

function onTouchStart(evt) {
  evt.preventDefault();
  if (evt.touches.length > 0) {
    let rect = CANVAS.getBoundingClientRect();
    let loc = {
      x: evt.touches[0].clientX - rect.left,
      y: evt.touches[0].clientY - rect.top,
    };
    SELECTED_PIECE = getPressedPiece(loc);
    if (SELECTED_PIECE) {
      SELECTED_PIECE.offsetX =
        loc.x - (BOARD_OFFSET_X + CELL_SIZE * (SELECTED_PIECE.piece.x + 0.5));
      SELECTED_PIECE.offsetY =
        loc.y - (BOARD_OFFSET_Y + CELL_SIZE * (SELECTED_PIECE.piece.y + 0.5));
      IS_SELECTED = true;
    }
  }
}

function onTouchMove(evt) {
  evt.preventDefault();
  if (SELECTED_PIECE != null && IS_SELECTED && evt.touches.length > 0) {
    let rect = CANVAS.getBoundingClientRect();
    SELECTED_PIECE.x =
      evt.touches[0].clientX - rect.left - SELECTED_PIECE.offsetX;
    SELECTED_PIECE.y =
      evt.touches[0].clientY - rect.top - SELECTED_PIECE.offsetY;
  }
}

function onTouchEnd(evt) {
  evt.preventDefault();
  if (SELECTED_PIECE != null) {
    let rect = CANVAS.getBoundingClientRect();
    let loc = {
      x: evt.changedTouches[0].clientX - rect.left,
      y: evt.changedTouches[0].clientY - rect.top,
    };
    let coords = getCoordinates(loc);

    if (coords.x !== -1 && coords.y !== -1) {
      SELECTED_PIECE.piece.x = coords.x;
      SELECTED_PIECE.piece.y = coords.y;

      server_move_request(CURRENT_STATUS, pieces);
    }

    SELECTED_PIECE = null;
    IS_SELECTED = false;
  }
}

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

function getPressedPiece(loc) {
  let coords = getCoordinates(loc);
  for (let i = 0; i < pieces.length; i++) {
    if (pieces[i].x === coords.x && pieces[i].y === coords.y) {
      return { piece: pieces[i], x: loc.x, y: loc.y };
    }
  }
  return null;
}

// DRAG AND DROP CODE

// RENDER CODE
function adjustScreen() {
  const size = Math.min(window.innerWidth * 0.9, window.innerHeight * 0.8);
  CANVAS.width = size;
  CANVAS.height = size;

  CELL_SIZE = CANVAS.height / 8;

  // Центрируем доску
  BOARD_OFFSET_X = (CANVAS.width - CELL_SIZE * 8) / 2;
  BOARD_OFFSET_Y = (CANVAS.height - CELL_SIZE * 8) / 2;

  CTX.clearRect(0, 0, CANVAS.width, CANVAS.height);
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
}

function draw_piece(piece, user_color) {
  let fillStyle = colors[piece.color];
  let strokeStyle = colors[piece.color ? 0 : 1];
  const X = BOARD_OFFSET_X + CELL_SIZE * (piece.x + 0.5);
  const Y = BOARD_OFFSET_Y + CELL_SIZE * (piece.y + 0.5);
  const radius = (CELL_SIZE / 2) * 0.8;
  draw_circle(X, Y, radius, 3, strokeStyle, fillStyle);
  draw_circle(X, Y, radius * 0.7, 3, strokeStyle, false);

  if (piece.mode !== "p") {
    draw_circle(X, Y, radius * 0.5, 6, "gold", "rgba(255, 215, 0, 0.7)");
  }
}

function draw_SELECTED_PIECE() {
  let fillStyle = colors[SELECTED_PIECE.piece.color];
  let strokeStyle = colors[SELECTED_PIECE.piece.color ? 0 : 1];
  const X = SELECTED_PIECE.x;
  const Y = SELECTED_PIECE.y;
  const radius = (CELL_SIZE / 2) * 0.8;
  draw_circle(X, Y, radius, 3, strokeStyle, fillStyle);
  draw_circle(X, Y, radius * 0.7, 3, strokeStyle, false);

  if (SELECTED_PIECE.piece.mode !== "p") {
    draw_circle(X, Y, radius * 0.5, 6, "gold", "rgba(255, 215, 0, 0.7)");
  }
}

function render_Board() {
  CTX.fillStyle = "#121212";
  CTX.fillRect(0, 0, CANVAS.width, CANVAS.height);

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
}

function render_Pieces() {
  for (let i = 0; i < pieces.length; i++) {
    if (SELECTED_PIECE?.piece === pieces[i]) {
      continue;
    }
    draw_piece(pieces[i], user_color);
  }
  if (SELECTED_PIECE) draw_SELECTED_PIECE();
}

function update() {
  render_Board();
  render_Pieces();
  window.requestAnimationFrame(update);
}
// RENDER CODE END
