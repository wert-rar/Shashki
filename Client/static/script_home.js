document.addEventListener('DOMContentLoaded', () => {
    const selectionModal = document.getElementById("selectionModal");
    const singleplayerBtn = document.getElementById("singleplayer-button");
    const playButton = document.getElementById("playButton");
    const selectedDifficulty = document.getElementById("selectedDifficulty");
    const selectedColor = document.getElementById("selectedColor");
    const hamburger = document.getElementById("hamburger");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    const bellDesktop = document.getElementById("bellDesktop");
    const bellMobile = document.getElementById("bellMobile");
    const notificationModal = document.getElementById("notificationModal");
    const closeNotificationModal = document.getElementById("closeNotificationModal");
    const notificationList = document.getElementById("notificationList");
    const bellDesktopCount = document.getElementById("bellDesktopCount");
    const bellMobileCount = document.getElementById("bellMobileCount");
    const friendsDesktop = document.getElementById("friendsDesktop");
    const friendsMobile = document.getElementById("friendsMobile");
    const friendsModal = document.getElementById("friendsModal");
    const closeFriendsModal = document.getElementById("closeFriendsModal");
    const friendsList = document.getElementById("friendsList");
    const removeFriendModal = document.getElementById("removeFriendModal");
    const removeFriendName = document.getElementById("removeFriendName");
    const confirmRemoveFriendButton = document.getElementById("confirmRemoveFriendButton");
    const cancelRemoveFriendButton = document.getElementById("cancelRemoveFriendButton");
    const multiplayerSelectionModal = document.getElementById("multiplayerSelectionModal");
    const multiplayerBtn = document.getElementById("multiplayer-button");
    const randomPlayerButton = document.getElementById("randomPlayerButton");
    const friendButton = document.getElementById("friendButton");
    const friendGameModal = document.getElementById("friendGameModal");
    const inviteFriendButton = document.getElementById("inviteFriendButton");
    const createRoomModal = document.getElementById("createRoomModal");
    const startGameButton = document.getElementById("startGameButton");
    const friendsToInvite = document.getElementById("friendsToInvite");
    const backToMultiplayerSelection = document.getElementById("backToMultiplayerSelection");

    let friendToRemove = null;

    let selections = { difficulty: null, color: null };
    let startX = 0;
    let endX = 0;
    let currentIndex = 0;
    let game_id = null;

    function fetchNotifications() {
        fetch('/get_notifications')
            .then(response => response.json())
            .then(data => {
                if (data.notifications && data.notifications.length > 0) {
                    notificationList.innerHTML = "";
                    data.notifications.forEach(sender => {
                        const notifItem = document.createElement("div");
                        notifItem.classList.add("notification-item");
                        notifItem.style.padding = "10px";
                        notifItem.style.borderBottom = "1px solid #444";

                        const notifText = document.createElement("p");
                        notifText.textContent = `Запрос в друзья от ${sender}`;
                        notifItem.appendChild(notifText);

                        const btnContainer = document.createElement("div");
                        btnContainer.style.marginTop = "5px";
                        btnContainer.style.display = "flex";
                        btnContainer.style.gap = "10px";

                        const acceptBtn = document.createElement("button");
                        acceptBtn.textContent = "Принять";
                        acceptBtn.style.flex = "1";
                        acceptBtn.style.padding = "5px";
                        acceptBtn.style.background = "#28a745";
                        acceptBtn.style.border = "none";
                        acceptBtn.style.borderRadius = "5px";
                        acceptBtn.style.cursor = "pointer";
                        acceptBtn.style.color = "#fff";
                        acceptBtn.addEventListener("click", (e) => {
                            e.stopPropagation();
                            respondFriendRequest(sender, "accept", notifItem);
                        });

                        const declineBtn = document.createElement("button");
                        declineBtn.textContent = "Отклонить";
                        declineBtn.style.flex = "1";
                        declineBtn.style.padding = "5px";
                        declineBtn.style.background = "#dc3545";
                        declineBtn.style.border = "none";
                        declineBtn.style.borderRadius = "5px";
                        declineBtn.style.cursor = "pointer";
                        declineBtn.style.color = "#fff";
                        declineBtn.addEventListener("click", (e) => {
                            e.stopPropagation();
                            respondFriendRequest(sender, "decline", notifItem);
                        });

                        btnContainer.appendChild(acceptBtn);
                        btnContainer.appendChild(declineBtn);
                        notifItem.appendChild(btnContainer);

                        notificationList.appendChild(notifItem);
                    });
                    updateNotificationCount(data.notifications.length);
                } else {
                    notificationList.innerHTML = "<p>Новых уведомлений нет</p>";
                    updateNotificationCount(0);
                }
            })
            .catch(err => {
                console.error("Ошибка при получении уведомлений:", err);
            });
    }

    function fetchFriends() {
        fetch('/get_friends')
            .then(response => response.json())
            .then(data => {
                friendsList.innerHTML = '';

                if (data.friends && data.friends.length > 0) {
                    data.friends.forEach(friend => {
                        const friendItem = document.createElement('div');
                        friendItem.classList.add('friend-item');

                        const profileLink = document.createElement('a');
                        profileLink.href = `/profile/${friend}`;
                        profileLink.textContent = friend;

                        friendItem.appendChild(profileLink);

                        const friendActions = document.createElement('div');
                        friendActions.classList.add('friend-actions');

                        const menuButton = document.createElement('button');
                        menuButton.classList.add('friend-actions-menu-button');
                        menuButton.innerHTML = '<i class="fas fa-ellipsis-v"></i>';

                        const menu = document.createElement('div');
                        menu.classList.add('friend-actions-menu', 'hide');

                        const removeButton = document.createElement('button');
                        removeButton.classList.add('remove-friend-button');
                        removeButton.setAttribute('data-friend', friend);
                        removeButton.textContent = 'Удалить из друзей';

                        menu.appendChild(removeButton);

                        friendActions.appendChild(menuButton);
                        friendActions.appendChild(menu);

                        friendItem.appendChild(friendActions);
                        friendsList.appendChild(friendItem);

                        menuButton.addEventListener('click', (e) => {
                            e.stopPropagation();
                            document.querySelectorAll('.friend-actions-menu.show').forEach((otherMenu) => {
                                if (otherMenu !== menu) {
                                    otherMenu.classList.remove('show');
                                }
                            });
                            menu.classList.toggle('show');
                        });

                        removeButton.addEventListener('click', () => {
                            friendToRemove = removeButton.getAttribute('data-friend');
                            removeFriendName.textContent = friendToRemove;
                            removeFriendModal.style.display = 'flex';
                            menu.classList.remove('show');
                        });
                    });
                } else {
                    friendsList.innerHTML = "<p>У вас пока нет друзей</p>";
                }
            })
            .catch(err => {
                console.error("Ошибка при получении друзей:", err);
                friendsList.innerHTML = "<p>Не удалось загрузить список друзей.</p>";
            });
    }

    document.addEventListener('click', (event) => {
        const isMenu = event.target.closest('.friend-actions-menu');
        const isMenuButton = event.target.closest('.friend-actions-menu-button');
        if (!isMenu && !isMenuButton) {
            document.querySelectorAll('.friend-actions-menu.show').forEach(openMenu => {
                openMenu.classList.remove('show');
            });
        }
    });

    function removeFriend(friendUsername) {
        fetch('/remove_friend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ friend_username: friendUsername })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                createNotification(data.error, "error");
            } else {
                createNotification(data.message, "success");
                fetchFriends();
            }
        })
        .catch(error => {
            createNotification("Ошибка при удалении друга", "error");
            console.error(error);
        });
    }

    confirmRemoveFriendButton.addEventListener('click', () => {
        if (friendToRemove) {
            removeFriend(friendToRemove);
        }
        friendToRemove = null;
        removeFriendModal.style.display = 'none';
    });

    cancelRemoveFriendButton.addEventListener('click', () => {
        removeFriendModal.style.display = 'none';
        friendToRemove = null;
    });

    function updateNotificationCount(count) {
        if (bellDesktopCount && bellMobileCount) {
            if (count > 0) {
                bellDesktopCount.textContent = count;
                bellMobileCount.textContent = count;
                bellDesktopCount.style.display = 'block';
                bellMobileCount.style.display = 'block';
            } else {
                bellDesktopCount.style.display = 'none';
                bellMobileCount.style.display = 'none';
            }
        }
    }

    function respondFriendRequest(sender, responseType, notifElement) {
        fetch('/respond_friend_request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender_username: sender, response: responseType })
        })
        .then(response => response.json())
        .then(data => {
            if (responseType === "accept") {
                createNotification(`Пользователь ${sender} теперь ваш друг`, "success");
                fetchFriends();
            } else {
                createNotification(`Вы отклонили запрос от ${sender}`, "error");
            }
            notifElement.remove();
            checkFriendRequests();
        })
        .catch(error => {
            createNotification("Ошибка при отправке ответа", "error");
            console.error(error);
        });
    }

    function createNotification(message, type) {
        let container = document.getElementById("notification-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "notification-container";
            document.body.appendChild(container);
        }

        const notification = document.createElement("div");
        notification.classList.add("notification", type);
        notification.innerHTML = message;

        const progressBar = document.createElement("div");
        progressBar.classList.add("progress-bar");
        notification.appendChild(progressBar);

        container.appendChild(notification);

        notification.addEventListener("click", () => {
            notification.style.transition = 'opacity 0.5s';
            notification.style.opacity = '0';
            setTimeout(() => {
                notification.remove();
            }, 500);
        });

        setTimeout(() => {
            notification.style.transition = 'opacity 0.5s';
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 500);
        }, 2000);
    }

    function checkFriendRequests() {
        fetch('/get_friend_requests')
            .then(response => response.json())
            .then(data => {
                if (bellDesktopCount && bellMobileCount) {
                    if (data.requests && data.requests.length > 0) {
                        bellDesktopCount.textContent = data.requests.length;
                        bellMobileCount.textContent = data.requests.length;
                        bellDesktopCount.style.display = 'block';
                        bellMobileCount.style.display = 'block';
                    } else {
                        bellDesktopCount.style.display = 'none';
                        bellMobileCount.style.display = 'none';
                    }
                }
            })
            .catch(error => console.error('Ошибка при получении запросов в друзья:', error));
    }

    checkFriendRequests();
    setInterval(checkFriendRequests, 5000);

    function toggleNotifications(event) {
        event.stopPropagation();
        if (notificationModal.classList.contains('active')) {
            notificationModal.classList.remove('active');
            bellDesktop.classList.remove('active');
            bellMobile.classList.remove('active');
        } else {
            if (friendsModal.classList.contains('active')) {
                friendsModal.classList.remove('active');
                friendsDesktop.classList.remove('active');
                friendsMobile.classList.remove('active');
            }
            notificationModal.classList.add('active');
            bellDesktop.classList.add('active');
            bellMobile.classList.add('active');
            fetchNotifications();
            updateNotificationCount(0);
        }
    }

    function toggleFriends(event) {
        event.stopPropagation();
        if (friendsModal.classList.contains('active')) {
            friendsModal.classList.remove('active');
            friendsDesktop.classList.remove('active');
            friendsMobile.classList.remove('active');
        } else {
            if (notificationModal.classList.contains('active')) {
                notificationModal.classList.remove('active');
                bellDesktop.classList.remove('active');
                bellMobile.classList.remove('active');
            }
            friendsModal.classList.add('active');
            friendsDesktop.classList.add('active');
            friendsMobile.classList.add('active');
            fetchFriends();
        }
    }

    if (bellDesktop) {
        bellDesktop.addEventListener('click', toggleNotifications);
        bellDesktop.addEventListener('touchend', (e) => {
            e.preventDefault();
            toggleNotifications(e);
        });
    }

    if (bellMobile) {
        bellMobile.addEventListener('click', toggleNotifications);
        bellMobile.addEventListener('touchend', (e) => {
            e.preventDefault();
            toggleNotifications(e);
        });
    }

    if (friendsDesktop) {
        friendsDesktop.addEventListener('click', toggleFriends);
        friendsDesktop.addEventListener('touchend', (e) => {
            e.preventDefault();
            toggleFriends(e);
        });
    }

    if (friendsMobile) {
        friendsMobile.addEventListener('click', toggleFriends);
        friendsMobile.addEventListener('touchend', (e) => {
            e.preventDefault();
            toggleFriends(e);
        });
    }

    multiplayerBtn.addEventListener('click', () => {
        multiplayerSelectionModal.style.display = "flex";
        overlay.classList.add("active");
    });

    friendButton.addEventListener('click', () => {
        multiplayerSelectionModal.style.display = "none";
        overlay.classList.remove("active");
        createRoomModal.style.display = "flex";
        overlay.classList.add("active");
        loadFriendsToInvite();
    });

    randomPlayerButton.addEventListener('click', () => {
        multiplayerSelectionModal.style.display = "none";
        overlay.classList.remove("active");
        startMultiplayerGame();
    });

    inviteFriendButton.addEventListener('click', () => {
        alert("Функциональность приглашения друзей пока не реализована.");
    });

    startGameButton.addEventListener('click', () => {
        const secondPlayerSlot = createRoomModal.querySelectorAll('.room-slots .slot')[1];
        if (secondPlayerSlot && secondPlayerSlot.textContent.trim() !== 'Друг') {
            startGameInRoom();
        } else {
            createNotification("Нужен второй игрок для начала игры.", "error");
        }
    });

    multiplayerSelectionModal.addEventListener('click', (event) => {
        if (event.target === multiplayerSelectionModal) {
            multiplayerSelectionModal.style.display = "none";
            overlay.classList.remove("active");
        }
    });

    friendGameModal.addEventListener('click', (event) => {
        if (event.target === friendGameModal) {
            friendGameModal.style.display = "none";
            overlay.classList.remove("active");
        }
    });

    createRoomModal.addEventListener('click', (event) => {
        if (event.target === createRoomModal) {
            createRoomModal.style.display = "none";
            overlay.classList.remove("active");
        }
    });

    backToMultiplayerSelection.addEventListener('click', () => {
        createRoomModal.style.display = "none";
        multiplayerSelectionModal.style.display = "flex";
        overlay.classList.add("active");
    });

    singleplayerBtn.onclick = function() {
        selectionModal.style.display = "flex";
        overlay.classList.add("active");
    };

    selectionModal.addEventListener('click', (event) => {
        if (event.target === selectionModal) {
            selectionModal.style.display = "none";
            overlay.classList.remove("active");
            resetSelections();
        }
    });

    if (!sidebar.classList.contains("active")) {
        sidebar.style.transform = 'translateX(300px)';
    }

    window.onclick = function(event) {
        if (!event.target.closest('#notificationModal') && !event.target.closest('#bellDesktop') && !event.target.closest('#bellMobile')) {
            notificationModal.classList.remove('active');
            bellDesktop.classList.remove('active');
            bellMobile.classList.remove('active');
        }
        if (!event.target.closest('#friendsModal') && !event.target.closest('#friendsDesktop') && !event.target.closest('#friendsMobile')) {
            friendsModal.classList.remove('active');
            friendsDesktop.classList.remove('active');
            friendsMobile.classList.remove('active');
        }
        if (!event.target.closest('#sidebar') && sidebar.classList.contains('active')) {
            closeSidebar();
        }
        if (!event.target.closest('#selectionModal') && !event.target.closest('#singleplayer-button')) {
            selectionModal.style.display = "none";
            overlay.classList.remove("active");
            resetSelections();
        }
        if (!event.target.closest('#multiplayerSelectionModal') && !event.target.closest('#multiplayer-button')) {
            multiplayerSelectionModal.style.display = "none";
            overlay.classList.remove("active");
        }
        if (!event.target.closest('#friendGameModal') && !event.target.closest('#friendButton')) {
            friendGameModal.style.display = "none";
            overlay.classList.remove("active");
        }
        if (!event.target.closest('#createRoomModal') && !event.target.closest('#friendButton')) {
            createRoomModal.style.display = "none";
            overlay.classList.remove("active");
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
        playButton.disabled = true;
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
            document.querySelectorAll('.swipe-wrapper .card').forEach((card, index) => {
                if(index === currentIndex){
                    card.classList.add('selected');
                } else {
                    card.classList.remove('selected');
                }
            });
            if (selectedColor.value && selectedDifficulty.value) {
                playButton.classList.add('active');
                playButton.disabled = false;
            } else {
                playButton.classList.remove('active');
                playButton.disabled = false;
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
        overlay.classList.add("active");
    };

    window.hideLeaveGameModal = function() {
        document.getElementById('leave-game-modal').style.display = 'none';
        overlay.classList.remove("active");
    };

    window.hideGameOverModal = function() {
        document.getElementById('game-over-modal').style.display = 'none';
        overlay.classList.remove("active");
    };

    window.leaveGame = function() {
        if (game_id && user_login) {
            fetch('/give_up', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ game_id: game_id, user_login: user_login })
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
        overlay.classList.add("active");
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
        if (window.innerWidth <= 1280 && friendsMobile) {
            friendsMobile.style.display = 'none';
        }
    }

    function closeSidebar() {
        sidebar.style.transition = 'transform 0.5s ease-out';
        sidebar.style.transform = 'translateX(300px)';
        overlay.classList.remove("active");
        hamburger.classList.remove("open");
        if (window.innerWidth <= 1280 && friendsMobile) {
            friendsMobile.style.display = 'block';
        }
        sidebar.addEventListener('transitionend', function handler() {
            sidebar.classList.remove("active");
            sidebar.removeEventListener('transitionend', handler);
        });
    }

    overlay.addEventListener("click", () => {
        closeSidebar();
        notificationModal.classList.remove('active');
        friendsModal.classList.remove('active');
        multiplayerSelectionModal.style.display = "none";
        friendGameModal.style.display = "none";
        createRoomModal.style.display = "none";
    });

    hamburger.addEventListener("click", (event) => {
        event.stopPropagation();
        if (sidebar.classList.contains("active")) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    if (window.innerWidth <= 1280) {
        sidebar.style.transform = 'translateX(300px)';
        let touchStartX = null;
        let currentTranslateX = 0;
        const sidebarWidth = sidebar.offsetWidth;
        sidebar.style.transition = 'none';
        sidebar.addEventListener("touchstart", (e) => {
            touchStartX = e.touches[0].clientX;
            sidebar.style.transition = 'none';
        }, { passive: true });
        sidebar.addEventListener("touchmove", (e) => {
            if (touchStartX === null) return;
            const touchCurrentX = e.touches[0].clientX;
            let deltaX = touchCurrentX - touchStartX;
            if (deltaX < 0) deltaX = 0;
            if (deltaX > sidebarWidth) deltaX = sidebarWidth;
            currentTranslateX = deltaX;
            sidebar.style.transform = `translateX(${deltaX}px)`;
        }, { passive: true });
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
            snowflake.style.opacity = Math.random().toString();
            snowflake.style.animationDuration = (Math.random() * 5 + 5) + 's';
            snowflake.style.animationDelay = Math.random() * 10 + 's';
            snowContainer.appendChild(snowflake);
        }
    }

    const notifications = document.querySelectorAll('.notification');
    notifications.forEach((notif) => {
        notif.addEventListener('click', () => {
            notif.remove();
        });
        setTimeout(() => {
            notif.style.transition = 'opacity 0.5s';
            notif.style.opacity = '0';
            setTimeout(() => {
                if (notif.parentNode) {
                    notif.parentNode.removeChild(notif);
                }
            }, 500);
        }, 2000);
    });

    function loadFriendsToInvite() {
        fetch('/get_friends')
            .then(response => response.json())
            .then(data => {
                friendsToInvite.innerHTML = '';
                if (data.friends && data.friends.length > 0) {
                    data.friends.forEach(friend => {
                        const friendInvite = document.createElement('div');
                        friendInvite.classList.add('friend-invite');

                        const friendName = document.createElement('span');
                        friendName.textContent = friend;

                        const inviteBtn = document.createElement('button');
                        inviteBtn.textContent = 'Пригласить';
                        inviteBtn.addEventListener('click', () => {
                            inviteFriend(friend);
                        });

                        friendInvite.appendChild(friendName);
                        friendInvite.appendChild(inviteBtn);
                        friendsToInvite.appendChild(friendInvite);
                    });
                } else {
                    friendsToInvite.innerHTML = "<p>У вас пока нет друзей для приглашения.</p>";
                }
            })
            .catch(err => {
                friendsToInvite.innerHTML = "<p>Не удалось загрузить список друзей.</p>";
                console.error("Ошибка при загрузке друзей для приглашения:", err);
            });
    }

    function inviteFriend(friendUsername) {
        fetch('/invite_friend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ friend_username: friendUsername })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                createNotification(data.error, "error");
            } else {
                createNotification(`Приглашение отправлено ${friendUsername}`, "success");
            }
        })
        .catch(error => {
            createNotification("Ошибка при отправке приглашения", "error");
            console.error(error);
        });
    }

    function startGameInRoom() {
        fetch('/start_room_game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_id: game_id })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                createNotification(data.error, "error");
            } else {
                window.location.href = `/board/${data.game_id}/${user_login}`;
            }
        })
        .catch(error => {
            createNotification("Ошибка при запуске игры", "error");
            console.error(error);
        });
    }
});
