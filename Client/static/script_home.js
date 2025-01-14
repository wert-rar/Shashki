document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById("selectionModal");
    const btn = document.getElementById("singleplayer-button");
    const span = document.getElementById("closeModal");
    const playButton = document.getElementById("playButton");
    const selectedDifficulty = document.getElementById("selectedDifficulty");
    const selectedColor = document.getElementById("selectedColor");
    const hamburger = document.getElementById("hamburger");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");

    let selections = { difficulty: null, color: null };
    let startX = 0;
    let endX = 0;
    let currentIndex = 0;

    if (!sidebar.classList.contains("active")) {
        sidebar.style.transform = 'translateX(300px)';
    }

    btn.onclick = function() {
        modal.style.display = "flex";
    };

    span.onclick = function() {
        modal.style.display = "none";
        resetSelections();
    };

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
            resetSelections();
        }
    };

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

    const isSmallScreen = window.innerWidth <= 530;

    if (!isSmallScreen) {
        document.querySelectorAll('.card[data-type="difficulty"]').forEach(function(card) {
            card.addEventListener('click', function() {
                let type = this.getAttribute('data-type');
                let value = this.getAttribute('data-value');
                if (this.classList.contains('selected')) {
                    this.classList.remove('selected');
                    selectedDifficulty.value = '';
                } else {
                    document.querySelectorAll(`.card[data-type="${type}"]`).forEach(function(otherCard) {
                        otherCard.classList.remove('selected');
                    });
                    this.classList.add('selected');
                    selectedDifficulty.value = value;
                }
                const difficulty = selectedDifficulty.value;
                const color = selectedColor.value;
                if (difficulty && color) {
                    playButton.classList.add('active');
                    playButton.disabled = false;
                } else {
                    playButton.classList.remove('active');
                    playButton.disabled = true;
                }
            });
        });
    } else {
        const swipeContainer = document.getElementById("difficultySwipe");
        const difficultyCards = swipeContainer.querySelectorAll('.card');

        function updateSwipe() {
            swipeContainer.style.transform = `translateX(-${currentIndex * 120}px)`;
            selectedDifficulty.value = difficultyCards[currentIndex].getAttribute('data-value');
            if (selectedColor.value && selectedDifficulty.value) {
                playButton.classList.add('active');
                playButton.disabled = false;
            } else {
                playButton.classList.remove('active');
                playButton.disabled = true;
            }
        }

        document.getElementById("rightArrow").addEventListener("click", () => {
            currentIndex = (currentIndex + 1) % difficultyCards.length;
            updateSwipe();
        });

        document.getElementById("leftArrow").addEventListener("click", () => {
            currentIndex = (currentIndex - 1 + difficultyCards.length) % difficultyCards.length;
            updateSwipe();
        });

        swipeContainer.addEventListener('touchstart', e => {
            startX = e.touches[0].clientX;
        }, false);

        swipeContainer.addEventListener('touchmove', e => {
            endX = e.touches[0].clientX;
        }, false);

        swipeContainer.addEventListener('touchend', () => {
            let deltaX = endX - startX;
            if (Math.abs(deltaX) > 30) {
                if (deltaX < 0) {
                    currentIndex = (currentIndex + 1) % difficultyCards.length;
                } else {
                    currentIndex = (currentIndex - 1 + difficultyCards.length) % difficultyCards.length;
                }
                updateSwipe();
            }
        }, false);

        updateSwipe();
    }

    document.querySelectorAll('.card[data-type="color"]').forEach(function(card) {
        card.addEventListener('click', function() {
            let type = this.getAttribute('data-type');
            let value = this.getAttribute('data-value');
            if (this.classList.contains('selected')) {
                this.classList.remove('selected');
                selectedColor.value = '';
            } else {
                document.querySelectorAll(`.card[data-type="${type}"]`).forEach(function(otherCard) {
                    otherCard.classList.remove('selected');
                });
                this.classList.add('selected');
                selectedColor.value = value;
            }
            const difficulty = selectedDifficulty.value;
            const color = selectedColor.value;
            if (difficulty && color) {
                playButton.classList.add('active');
                playButton.disabled = false;
            } else {
                playButton.classList.remove('active');
                playButton.disabled = true;
            }
        });
    });

    window.startMultiplayerGame = function() {
        window.location.href = '/start_game';
    };

    window.returnToGame = function() {
        if (game_id && user_login) {
            window.location.href = `/board/${game_id}/${user_login}`;
        } else {
            alert("Активная игра не найдена.");
        }
    };

    window.showLeaveGameModal = function() {
        document.getElementById('leave-game-modal').style.display = 'flex';
    };

    window.hideLeaveGameModal = function() {
        document.getElementById('leave-game-modal').style.display = 'none';
    };

    window.hideGameOverModal = function() {
        document.getElementById('game-over-modal').style.display = 'none';
    };

    window.leaveGame = function() {
        if (game_id && user_login) {
            fetch('/give_up', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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
                alert('Произошла ошибка при покидании игры.');
            });
        } else {
            alert("Активная игра не найдена.");
        }
    };

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
        message.innerHTML = `${resultText}<br>${points_text}`;
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
                document.getElementById('return-to-game').style.display = 'none';
            });
    }

    function openSidebar() {
        sidebar.classList.add("active");
        sidebar.style.transition = 'transform 0.3s ease-out';
        sidebar.style.transform = 'translateX(0)';
        overlay.classList.add("active");
        hamburger.classList.add("open");
    }

    function closeSidebar() {
        sidebar.style.transition = 'transform 0.5s ease-out';
        sidebar.style.transform = 'translateX(300px)';
        overlay.classList.remove("active");
        hamburger.classList.remove("open");
        sidebar.addEventListener('transitionend', function handler() {
            sidebar.classList.remove("active");
            sidebar.removeEventListener('transitionend', handler);
        });
    }

    overlay.addEventListener("click", () => {
        closeSidebar();
    });

    hamburger.addEventListener("click", () => {
        if (sidebar.classList.contains("active")) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    if (window.innerWidth <= 530) {
        sidebar.style.transform = 'translateX(300px)';
        let touchStartX = null;
        let currentTranslateX = 0;
        const sidebarWidth = sidebar.offsetWidth;

        sidebar.style.transition = 'none';

        sidebar.addEventListener("touchstart", (e) => {
            touchStartX = e.touches[0].clientX;
            sidebar.style.transition = 'none';
        }, false);

        sidebar.addEventListener("touchmove", (e) => {
            if (touchStartX === null) return;
            const touchCurrentX = e.touches[0].clientX;
            let deltaX = touchCurrentX - touchStartX;
            if (deltaX < 0) deltaX = 0;
            if (deltaX > sidebarWidth) deltaX = sidebarWidth;
            currentTranslateX = deltaX;
            sidebar.style.transform = `translateX(${deltaX}px)`;
        }, false);

        sidebar.addEventListener("touchend", () => {
            sidebar.style.transition = 'transform 0.5s ease-out';

            if (currentTranslateX > sidebarWidth / 3) {
                closeSidebar();
            } else {
                sidebar.style.transform = 'translateX(0)';
            }

            touchStartX = null;
            currentTranslateX = 0;
        }, false);
    }

    function handlePageShow(event) {
        if (event.persisted) {
            checkForActiveGame();
        }
    }

    checkForActiveGame();
    setInterval(checkForActiveGame, 5000);

    createSnowflakes();

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

document.addEventListener('DOMContentLoaded', function() {
    const notifications = document.querySelectorAll('.notification');
    notifications.forEach((notif) => {
        notif.addEventListener('click', () => {
            notif.remove();
        });
        setTimeout(() => {
            notif.remove();
        }, 2000);
    });
});
