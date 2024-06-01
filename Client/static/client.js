// TODO:

let CANVAS = null;
let CTX = null;
let SELECTED_PIECE = null;
let CELL_SIZE = 0;
let HEADER_HEIGHT = 0;
let CURRENT_STATUS = "w1";
let SERVER_IP = "";

let status = {
  w1: "Ход белых",
  b1: "Ход черных",
  w2: "Нельзя двигать фигуру, сейчас ход белых",
  b2: "Нельзя двигать фигуру, сейчас ход черных",
  w3: "Победили белые",
  b3: "Победили черные",
  w4:"Белые продолжают ход",
  b4:"Черные продолжают ход",
  e1:"Ошибка при запросе к серверу"
};
let colors = {
  1: "rgb(0,0,0)",
  0: "rgb(255,255,255)"
};
let b_colors = {
  1: "#DA7422",
  0: "#FFFBDB"
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
  { color: 0, x: 0, y: 7, mode: "p" },
  { color: 0, x: 2, y: 7, mode: "p" },
  { color: 0, x: 4, y: 7, mode: "p" },
  { color: 0, x: 6, y: 7, mode: "p" },
  { color: 0, x: 1, y: 6, mode: "p" },
  { color: 0, x: 3, y: 6, mode: "p" },
  { color: 0, x: 5, y: 6, mode: "p" },
  { color: 0, x: 7, y: 6, mode: "p" },
  { color: 0, x: 0, y: 5, mode: "p" },
  { color: 0, x: 2, y: 5, mode: "p" },
  { color: 0, x: 4, y: 5, mode: "p" },
  { color: 0, x: 6, y: 5, mode: "p" },
];

// GAMEPLAY CODE
function update_data(data){
  CURRENT_STATUS = data.status_;
  pieces = data.pieces;
  document.getElementById("status").innerHTML = status[CURRENT_STATUS];
  update();
}
function server_request(status,pieces){
  let body = {status_:status,pieces:pieces}
  console.log('post request data');
  console.log(body);
  let xhr = new XMLHttpRequest();
  xhr.open('POST','/move');
  xhr.addEventListener('load',function(){
     if(xhr.status === 200 && xhr.readyState ===4){
      let response = JSON.parse(xhr.responseText);
    update_data(response);
    console.log('response data');
    console.log(response);
     }
     else {
     update_data({status_:'e1',pieces:pieces})
     throw new Error('bad request');
     }
  });
  xhr.setRequestHeader('Content-type','application/json');
  xhr.send(JSON.stringify(body));
}
//
//
// function win(stat) {
//   if (stat == "b3")
//     document.getElementsByClassName("board")[0].innerHTML =
//       "<div class='win'> Победили черные</div>";
//   else
//     document.getElementsByClassName("board")[0].innerHTML =
//       "<div class='win'> Победили белые</div>";
// }

function onLoad() {
  CANVAS = document.getElementById("board");
  CTX = CANVAS.getContext("2d");
  HEADER_HEIGHT = document.getElementsByClassName("header")[0].clientHeight;

  adjustScreen();
  update();
  addEventListeners();
}

// DRAG AND DROP CODE
function addEventListeners() {
  CANVAS.addEventListener("mousedown", onMouseDown);
  CANVAS.addEventListener("mousemove", onMouseMove);
  CANVAS.addEventListener("mouseup", onMouseUp);
  CANVAS.addEventListener("touchstart", onTouchStart);
  CANVAS.addEventListener("touchmove", onTouchMove);
  CANVAS.addEventListener("touchend", onTouchEnd);
}

function onMouseDown(evt) {
  evt.preventDefault();
  SELECTED_PIECE = getPressedPiece(evt);
  if (SELECTED_PIECE) {
    SELECTED_PIECE.y = evt.y - HEADER_HEIGHT;
  }
}

function onMouseMove(evt) {
  evt.preventDefault();
  if (SELECTED_PIECE != null) {
    SELECTED_PIECE.x = evt.x;
    SELECTED_PIECE.y = evt.y - HEADER_HEIGHT;
  }
}

function onMouseUp(evt) {
  evt.preventDefault();
  if (SELECTED_PIECE != null) {

    let coords = getCoordinates(evt);
    SELECTED_PIECE.piece.x = coords.x;
    SELECTED_PIECE.piece.y = coords.y;
    SELECTED_PIECE = null;
    server_request(CURRENT_STATUS,pieces);
  }
}

function onTouchStart(evt) {
  let loc = {
    x: evt.touches[0].clientX,
    y: evt.touches[0].clientY,
  };
  onMouseDown(loc);
}

function onTouchMove(evt) {
  let loc = {
    x: evt.touches[0].clientX,
    y: evt.touches[0].clientY,
  };
  onMouseMove(loc);
}

function onTouchEnd(evt) {
  let loc = {
    x: evt.touches[0].clientX,
    y: evt.touches[0].clientY,
  };
  onMouseUp(loc);
}

function getCoordinates(loc) {

  for (let i = 0; i < 8; i++) {
    let y_range = (i + 1) * CELL_SIZE + HEADER_HEIGHT;
    if (y_range < loc.y && loc.y < y_range + CELL_SIZE) {
      for (let j = 0; j < 8; j++) {
        let x_range = (j + 1) * CELL_SIZE;
        if (x_range < loc.x && loc.x < x_range + CELL_SIZE) return { x: j, y: i };
      }
    }
  }
  return { x: -1, y: -1 };
}

function getPressedPiece(loc) {
  let coords = getCoordinates(loc);
  for (let i = 0; i < pieces.length; i++) {
    if (pieces[i].x == coords.x && pieces[i].y == coords.y)
      return { piece: pieces[i], x: loc.x, y: loc.y };
  }

  return null;
}

// DRAG AND DROP CODE

// RENDER CODE
function adjustScreen() {
  CANVAS.width = window.innerWidth;
  CANVAS.height = window.innerHeight * 0.9;
  CELL_SIZE = CANVAS.height * 0.1;
  console.log(CELL_SIZE);
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

function draw_piece(piece) {
  let fillStyle = colors[piece.color];
  let strokeStyle = colors[piece.color ? 0 : 1];
  const X = CELL_SIZE * (piece.x + 1.5);
  const Y = CELL_SIZE * (piece.y + 1.5);
  const radius = (CELL_SIZE / 2) * 0.8;
  draw_circle(X, Y, radius, 3, strokeStyle, fillStyle);
  draw_circle(X, Y, radius * 0.7, 3, strokeStyle, false);

  if (piece.mode != "p") {
    draw_circle(X, Y, radius * 0.5, 6, "gold");
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

  if (SELECTED_PIECE.piece.mode != "p") {
    draw_circle(X, Y, radius * 0.5, 6, "gold");
  }
}

function render_Board() {
  CTX.fillStyle = "white";
  CTX.fillRect(0, 0, CANVAS.width, CANVAS.height);

  

  let step = 0;
  for (let i = 0; i < 8; i++) {
    for (let j = 0; j < 8; j++) {
      CTX.fillStyle = b_colors[step % 2];
      CTX.fillRect(
        CELL_SIZE + CELL_SIZE * j,
        CELL_SIZE + CELL_SIZE * i,
        CELL_SIZE,
        CELL_SIZE
      );
      step++;
    }
    step++;
  }
}

function render_Pieces() {
  for (let i = 0; i < pieces.length; i++) {
    if (SELECTED_PIECE?.piece == pieces[i]) {
      continue;
    }
    draw_piece(pieces[i]);
  }
  if (SELECTED_PIECE) draw_SELECTED_PIECE();
}

function update() {
  render_Board();
  render_Pieces();
  window.requestAnimationFrame(update);
}
// RENDER CODE END
