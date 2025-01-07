document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById("selectionModal");
    const btn = document.getElementById("singleplayer-button");
    const span = document.getElementById("closeModal");
    const playButton = document.getElementById("playButton");
    const selectedDifficulty = document.getElementById("selectedDifficulty");
    const selectedColor = document.getElementById("selectedColor");

    let selections = {
        difficulty: null,
        color: null
    };

    btn.onclick = function() {
        modal.style.display = "flex";
    }

    span.onclick = function() {
        modal.style.display = "none";
        resetSelections();
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
            resetSelections();
        }
    }

    document.querySelectorAll('.card').forEach(function(card) {
        card.addEventListener('click', function() {
            let type = this.getAttribute('data-type');
            let value = this.getAttribute('data-value');

            if (this.classList.contains('selected')) {
                this.classList.remove('selected');
                selections[type] = null;

                if (type === 'difficulty') selectedDifficulty.value = '';
                if (type === 'color') selectedColor.value = '';
            } else {
                document.querySelectorAll(`.card[data-type="${type}"]`).forEach(function(otherCard) {
                    otherCard.classList.remove('selected');
                });

                this.classList.add('selected');
                selections[type] = value;

                if (type === 'difficulty') selectedDifficulty.value = value;
                if (type === 'color') selectedColor.value = value;
            }

            if (selections.difficulty && selections.color) {
                playButton.classList.add('active');
            } else {
                playButton.classList.remove('active');
            }
        });
    });

    function resetSelections() {
        selections.difficulty = null;
        selections.color = null;

        selectedDifficulty.value = '';
        selectedColor.value = '';

        document.querySelectorAll('.card').forEach(function(card) {
            card.classList.remove('selected');
        });

        playButton.classList.remove('active');
    }

    window.startMultiplayerGame = function() {
        window.location.href = '/start_game';
    }

    window.returnToGame = function() {
        if (game_id && user_login) {
            window.location.href = `/board/${game_id}/${user_login}`;
        } else {
            alert("Активная игра не найдена.");
        }
    }

    window.showLeaveGameModal = function() {
        document.getElementById('leave-game-modal').style.display = 'flex';
    }

    window.hideLeaveGameModal = function() {
        document.getElementById('leave-game-modal').style.display = 'none';
    }

    window.hideGameOverModal = function() {
        document.getElementById('game-over-modal').style.display = 'none';
    }

    window.leaveGame = function() {
        if (game_id && user_login) {
            fetch('/give_up', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({game_id: game_id, user_login: user_login})
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    hideLeaveGameModal();
                    document.getElementById('return-to-game').style.display = 'none';
                    displayGameOverMessage(data);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Произошла ошибка при покидании игры.');
            });
        } else {
            alert("Активная игра не найдена.");
        }
    }

    function displayGameOverMessage(data) {
        const modal = document.getElementById("game-over-modal");
        const message = document.getElementById("game-over-message");

        let resultText = "";
        if (data.result === "win") {
            resultText = "Поздравляем! Вы победили!";
        } else if (data.result === "lose") {
            resultText = "Вы проиграли.";
        } else if (data.result === "draw") {
            resultText = "Ничья.";
        }

        let points_gained = data.points_gained || 0;
        let points_text = points_gained >= 0 ? `Вы получили ${points_gained} очков к рангу.` : `Вы потеряли ${Math.abs(points_gained)} очков к рангу.`;

        message.innerHTML = `
            ${resultText}<br>
            ${points_text}
        `;

        modal.style.display = "flex";
    }

    function checkForActiveGame() {
        fetch('/check_game_status')
            .then(response => {
                if (response.status === 200) {
                    return response.json();
                } else {
                    throw new Error('Нет активной игры.');
                }
            })
            .then(data => {
                if (data.status === 'active') {
                    if (data.game_id) {
                        game_id = data.game_id;
                    }
                    document.getElementById('return-to-game').style.display = 'block';
                } else {
                    document.getElementById('return-to-game').style.display = 'none';
                }
            })
            .catch(error => {
                console.log(error.message);
                document.getElementById('return-to-game').style.display = 'none';
            });
    }

    function handlePageShow(event) {
        if (event.persisted) {
            checkForActiveGame();
        }
    }

    checkForActiveGame();
    setInterval(checkForActiveGame, 5000);
    createSnowflakes();

    if (messages && messages.length > 0) {
        messages.forEach(function(message) {
            let category = message[0];
            let text = message[1];
            let icon = 'info';
            let title = 'Информация';

            if (category === 'success') {
                icon = 'success';
                title = 'Успех';
            } else if (category === 'error') {
                icon = 'error';
                title = 'Ошибка';
            } else if (category === 'info') {
                icon = 'info';
                title = 'Информация';
            }

            Swal.fire({
                icon: icon,
                title: title,
                text: text,
                background: '#1e1e2e',
                color: '#fff',
                confirmButtonColor: category === 'error' ? '#e74c3c' : '#2ecc71'
            });
        });
    }

    window.addEventListener('pageshow', handlePageShow);

    function createSnowflakes() {
        const snowContainer = document.getElementById('snow-container');
        const snowflakeCount = 50;

        for (let i = 0; i < snowflakeCount; i++) {
            const snowflake = document.createElement('div');
            snowflake.classList.add('snowflake');
            snowflake.textContent = '❄';
            snowflake.style.left = Math.random() * 100 + 'vw';
            snowflake.style.fontSize = (Math.random() * 10 + 10) + 'px';
            snowflake.style.opacity = Math.random();
            snowflake.style.animationDuration = (Math.random() * 5 + 5) + 's';
            snowflake.style.animationDelay = Math.random() * 10 + 's';
            snowContainer.appendChild(snowflake);
        }
    }
});
