document.addEventListener('DOMContentLoaded', () => {
    const modalOverlay = document.getElementById('modalOverlay');
    modalOverlay.style.display = 'none';
    let pollInterval = null;
    const slot1 = document.getElementById('slot1');
    const slot2 = document.getElementById('slot2');
    const startGameButton = document.getElementById('startGameButton');
    const menuBtn = document.getElementById('menuBtn');
    const dropdownMenu = document.getElementById('dropdownMenu');
    let currentOccupant = "";

    const colorWhite = document.getElementById('colorWhite');
    const colorBlack = document.getElementById('colorBlack');
    const whiteName = document.getElementById('whiteName');
    const blackName = document.getElementById('blackName');

    window.inviteFriend = function(friendUsername, button) {
        fetch('/invite_friend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ friend_username: friendUsername, room_id: currentRoomId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                createNotification(data.error, "error");
            } else {
                createNotification("Приглашение отправлено", "success");
                button.textContent = 'В ожидании';
                button.disabled = true;
            }
        })
        .catch(() => {
            createNotification("Ошибка при приглашении друга", "error");
        });
    };

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

    colorWhite.addEventListener('click', () => {
        toggleColorSelection('w');
    });
    colorBlack.addEventListener('click', () => {
        toggleColorSelection('b');
    });

function toggleColorSelection(color) {
    fetch('/select_color', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_id: currentRoomId, color: color })
    })
    .then(res => res.json())
    .then(data => {
        console.log("Ответ от /select_color:", data);
        if (data.error) {
            createNotification(data.error, "error");
        } else {
            if (data.message) {
                createNotification(data.message, "success");
            }
            updateColorDisplay(data);
        }
    })
    .catch(() => {
        createNotification("Ошибка при выборе цвета", "error");
    });
}

    function updateColorDisplay(data) {
        if(data.chosen_white) {
            colorWhite.classList.add('selected');
            whiteName.textContent = data.chosen_white;
        } else {
            colorWhite.classList.remove('selected');
            whiteName.textContent = "";
        }
        if(data.chosen_black) {
            colorBlack.classList.add('selected');
            blackName.textContent = data.chosen_black;
        } else {
            colorBlack.classList.remove('selected');
            blackName.textContent = "";
        }
        if(startGameButton) {
            if(data.chosen_white && data.chosen_black) {
                startGameButton.disabled = false;
            } else {
                startGameButton.disabled = true;
            }
        }
    }

    if(startGameButton) {
        startGameButton.addEventListener('click', () => {
            fetch('/start_room_game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ room_id: currentRoomId })
            })
            .then(res => res.json())
            .then(data => {
                if(data.error) {
                    createNotification(data.error, "error");
                } else {
                    window.location.href = `/board/${data.game_id}/${user_login}`;
                }
            })
            .catch(() => {
                createNotification("Ошибка при запуске игры", "error");
            });
        });
    }

    startPollingRoomStatus();

    const modalTitle = document.getElementById('modalTitle');
    const profileBtn = document.getElementById('profileBtn');
    const kickBtn = document.getElementById('kickBtn');
    const transferBtn = document.getElementById('transferBtn');
    function openModal(occupant) {
        currentOccupant = occupant;
        modalTitle.textContent = `Действия с ${occupant}`;
        modalOverlay.style.display = 'flex';
    }
    profileBtn.addEventListener('click', () => {
        if (currentOccupant && currentOccupant !== "Ожидание...") {
            window.location.href = '/profile/' + currentOccupant;
        }
        closeModal();
    });
    function closeModal() {
        modalOverlay.style.display = 'none';
    }
    modalOverlay.addEventListener('click', (e) => {
        if(e.target === modalOverlay) closeModal();
    });
    slot1.addEventListener('click', () => {
        const occupant = slot1.querySelector('p').textContent.trim();
        if (occupant && occupant !== "Ожидание...") {
            window.location.href = '/profile/' + occupant + '?origin=room';
        }
    });
    slot2.addEventListener('click', () => {
        const occupant = slot2.querySelector('p').textContent.trim();
        if (occupant && occupant !== "Ожидание...") {
            if (!is_creator) {
                window.location.href = '/profile/' + occupant + '?origin=room';
            }
            else {
                openModal(occupant);
            }
        }
    });
    kickBtn.addEventListener('click', () => {
        const occupant = slot2.querySelector('p').textContent.trim();
        fetch('/kick_user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_id: currentRoomId, kicked_user: occupant })
        })
        .then(res => res.json())
        .then(data => {
            if(data.error) {
                createNotification(data.error, "error");
            } else {
                createNotification(data.message, "success");
                window.location.reload();
            }
            closeModal();
        })
        .catch(() => {
            createNotification("Ошибка при выполнении запроса", "error");
            closeModal();
        });
    });
    transferBtn.addEventListener('click', () => {
        const occupant = slot2.querySelector('p').textContent.trim();
        fetch('/transfer_leader', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_id: currentRoomId, new_leader: occupant })
        })
        .then(res => res.json())
        .then(data => {
            if(data.error) {
                createNotification(data.error, "error");
            } else {
                createNotification(data.message, "success");
                slot1.querySelector('p').textContent = occupant;
                slot2.querySelector('p').textContent = user_login;
                is_creator = false;
                const friendsListContainer = document.querySelector('.friends-list');
                if(friendsListContainer) friendsListContainer.style.display = 'none';
                if(startGameButton) startGameButton.style.display = 'none';
            }
            closeModal();
        })
        .catch(() => {
            createNotification("Ошибка при выполнении запроса", "error");
            closeModal();
        });
    });
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
                if (notification.parentNode) notification.parentNode.removeChild(notification);
            }, 500);
        });
        setTimeout(() => {
            notification.style.opacity = "0";
            setTimeout(() => {
                if (notification.parentNode) notification.parentNode.removeChild(notification);
            }, 500);
        }, 2000);
    }
    function startPollingRoomStatus() {
        if (pollInterval) return;
        pollInterval = setInterval(() => {
            if (!currentRoomId) return;
            fetch(`/check_room_status?room_id=${currentRoomId}`)
            .then(res => res.json())
            .then(data => {
                if (data.redirect) {
                    window.location.href = data.redirect;
                    return;
                }
                if(data.status === "kicked") {
                    window.location.href = '/';
                    return;
                }
                if (data.error) {
                    if (data.error === "Комната не найдена") {
                        setTimeout(() => {
                            window.location.href = '/?room_status=deleted';
                        }, 500);
                    }
                    return;
                }
                if (data.creator) {
                    const creatorText = document.querySelector('#slot1 p');
                    creatorText.textContent = data.creator;
                    if (data.creator === user_login && !is_creator) {
                        is_creator = true;
                        window.location.reload();
                    } else if (data.creator !== user_login) {
                        is_creator = false;
                    }
                    const friendsListContainer = document.querySelector('.friends-list');
                    if(is_creator && friendsListContainer) {
                        friendsListContainer.style.display = 'block';
                        if(startGameButton) startGameButton.style.display = 'block';
                    } else if(friendsListContainer) {
                        friendsListContainer.style.display = 'none';
                        if(startGameButton) startGameButton.style.display = 'none';
                    }
                }
                if (data.joined_user) {
                    slot2.innerHTML = `<p>${data.joined_user}</p>`;
                    const friendInvites = document.querySelectorAll('.friend-invite');
                    friendInvites.forEach(invite => {
                        const friendName = invite.querySelector('span').textContent.trim();
                        const btn = invite.querySelector('button');
                        if (friendName === data.joined_user) {
                            btn.textContent = 'В комнате';
                            btn.classList.remove('waiting-btn');
                            btn.classList.add('in-room-btn');
                        }
                    });
                } else {
                    slot2.innerHTML = `<p>Ожидание...</p>`;
                    const friendInvites = document.querySelectorAll('.friend-invite');
                    friendInvites.forEach(invite => {
                        const btn = invite.querySelector('button');
                        if (btn.classList.contains('in-room-btn')) {
                            btn.textContent = 'Пригласить';
                            btn.classList.remove('in-room-btn');
                        }
                    });
                }
                if(data.chosen_white !== undefined && data.chosen_black !== undefined) {
                    updateColorDisplay({chosen_white: data.chosen_white, chosen_black: data.chosen_black});
                }
                if(data.invited_friends) {
                    document.querySelectorAll('.friend-invite').forEach(invite => {
                        const friendName = invite.querySelector('span').textContent.trim();
                        const btn = invite.querySelector('button');
                        if(data.invited_friends.hasOwnProperty(friendName)) {
                            if(data.invited_friends[friendName] === "declined") {
                                btn.textContent = "Отклонено";
                                btn.disabled = false;
                                btn.classList.remove("waiting-btn");
                                btn.classList.add("declined-btn");
                            } else {
                                btn.textContent = "В ожидании";
                                btn.disabled = true;
                                btn.classList.remove("declined-btn");
                                btn.classList.add("waiting-btn");
                            }
                        } else {
                            btn.textContent = "Пригласить";
                            btn.disabled = false;
                            btn.classList.remove("waiting-btn", "declined-btn");
                        }
                    });
                }
            })
            .catch(() => {});
        }, 1000);
    }
});
