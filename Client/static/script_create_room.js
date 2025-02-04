document.addEventListener('DOMContentLoaded', () => {
    let pollInterval = null;
    const slot1 = document.getElementById('slot1');
    const slot2 = document.getElementById('slot2');
    const friendsToInvite = document.getElementById('friendsToInvite');
    const startGameButton = document.getElementById('startGameButton');
    const invitedFriends = {};
    const slot1Text = document.querySelector('#slot1 p');
    slot1Text.textContent = user_login;

    const menuBtn = document.getElementById('menuBtn');
    const dropdownMenu = document.getElementById('dropdownMenu');
    menuBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdownMenu.style.display = dropdownMenu.style.display === 'block' ? 'none' : 'block';
    });
    document.addEventListener('click', () => {
        dropdownMenu.style.display = 'none';
    });

    const leaveRoomBtn = document.getElementById('leaveRoomBtn');
    if (leaveRoomBtn) {
        leaveRoomBtn.addEventListener('click', () => {
            fetch('/leave_room', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ room_id: currentRoomId })
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    createNotification(data.error, "error");
                } else {
                    createNotification(data.message, "success");
                    window.location.href = '/';
                }
            })
            .catch(() => {
                createNotification("Ошибка при выходе из комнаты", "error");
            });
        });
    }
    const deleteRoomBtn = document.getElementById('deleteRoomBtn');
    if (deleteRoomBtn) {
        deleteRoomBtn.addEventListener('click', () => {
            fetch('/delete_room', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ room_id: currentRoomId })
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    createNotification(data.error, "error");
                } else {
                    createNotification(data.message, "success");
                    window.location.href = '/';
                }
            })
            .catch(() => {
                createNotification("Ошибка при удалении комнаты", "error");
            });
        });
    }

    if (is_creator && friendsToInvite) {
        loadFriendsToInvite();
    }

    startPollingRoomStatus();

    function createNotification(message, type) {
        const container = document.getElementById("notification-container");
        const notification = document.createElement("div");
        notification.classList.add("notification", type);
        notification.innerHTML = message;
        const progressBar = document.createElement("div");
        progressBar.classList.add("progress-bar");
        notification.appendChild(progressBar);
        container.appendChild(notification);
        notification.addEventListener("click", () => {
            notification.style.opacity = "0";
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 500);
        });
        setTimeout(() => {
            notification.style.opacity = "0";
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 500);
        }, 2000);
    }

    function startPollingRoomStatus() {
        if (pollInterval) return;
        pollInterval = setInterval(() => {
            if (!currentRoomId) return;
            fetch(`/check_room_status?game_id=${currentRoomId}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    if (data.error === "Комната не найдена") {
                        setTimeout(() => {
                            window.location.href = '/?room_status=deleted';
                        }, 1000);
                    }
                    return;
                }
                if (data.creator) {
                    const creatorText = document.querySelector('#slot1 p');
                    creatorText.textContent = data.creator;
                    if (data.creator === user_login && !is_creator) {
                        is_creator = true;
                        window.location.reload();
                    }
                }
                if (data.joined_user) {
                    slot2.innerHTML = `<p>${data.joined_user}</p>`;
                } else {
                    slot2.innerHTML = `<p>Ожидание...</p>`;
                }
                if (data.game_status === 'current' || data.game_status === 'active') {
                    window.location.href = `/board/${currentRoomId}/${user_login}`;
                }
                if (is_creator && friendsToInvite) {
                    updateFriendsUI(data.joined_user);
                }
            })
            .catch(() => {});
        }, 1000);
    }

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
                        inviteFriend(friend, inviteBtn);
                    });
                    friendInvite.appendChild(friendName);
                    friendInvite.appendChild(inviteBtn);
                    friendsToInvite.appendChild(friendInvite);
                });
            } else {
                friendsToInvite.innerHTML = "<p>У вас пока нет друзей для приглашения.</p>";
            }
        })
        .catch(() => {
            friendsToInvite.innerHTML = "<p>Не удалось загрузить список друзей.</p>";
        });
    }

    function inviteFriend(friendUsername, button) {
        if (!currentRoomId) return;
        fetch('/invite_friend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ friend_username: friendUsername, game_id: currentRoomId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                createNotification(data.error, "error");
            } else {
                createNotification("Приглашение отправлено", "success");
                invitedFriends[friendUsername] = true;
                button.textContent = 'В ожидании';
                button.classList.add('waiting-btn');
            }
        })
        .catch(() => {
            createNotification("Ошибка при приглашении друга", "error");
        });
    }

    function updateFriendsUI(occupant) {
        const friendInvites = friendsToInvite.querySelectorAll('.friend-invite');
        friendInvites.forEach(invite => {
            const friendName = invite.querySelector('span').textContent;
            const btn = invite.querySelector('button');
            if (friendName === occupant) {
                btn.textContent = 'В комнате';
                btn.classList.remove('waiting-btn');
                btn.classList.add('in-room-btn');
            } else {
                if (invitedFriends[friendName]) {
                    btn.textContent = 'В ожидании';
                    btn.classList.remove('in-room-btn');
                    btn.classList.add('waiting-btn');
                } else {
                    btn.textContent = 'Пригласить';
                    btn.classList.remove('waiting-btn', 'in-room-btn');
                }
            }
        });
    }

    if (is_creator && startGameButton) {
        startGameButton.addEventListener('click', () => {
            if (slot2.textContent.trim() === 'Ожидание...') {
                createNotification("Нужен второй игрок для начала игры", "error");
            } else {
                startGameInRoom();
            }
        });
    }

    function startGameInRoom() {
        if (!currentRoomId) {
            createNotification("Комната не найдена", "error");
            return;
        }
        fetch('/start_room_game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_id: currentRoomId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                createNotification(data.error, "error");
            } else {
                createNotification("Игра запущена", "success");
            }
        })
        .catch(() => {
            createNotification("Ошибка при запуске игры", "error");
        });
    }
});
