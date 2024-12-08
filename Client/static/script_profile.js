function logout() {
    window.location.href = '/logout';
}

function goHome() {
    window.location.href = '/';
}

function returnToGame() {
    const gameId = profileData.gameId;
    const userLogin = profileData.currentUserLogin;
    window.location.href = `/board/${gameId}/${userLogin}`;
}

document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('statsChart').getContext('2d');
    const statsChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Победы', 'Ничьих', 'Поражений'],
            datasets: [{
                data: [profileData.wins, profileData.draws, profileData.losses],
                backgroundColor: [
                    'rgba(46, 204, 113, 0.7)',
                    'rgba(241, 196, 15, 0.7)',
                    'rgba(231, 76, 60, 0.7)'
                ],
                borderColor: [
                    'rgba(46, 204, 113, 1)',
                    'rgba(241, 196, 15, 1)',
                    'rgba(231, 76, 60, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            size: 14
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Статистика Игры',
                    font: {
                        size: 18
                    },
                    color: 'white'
                }
            }
        },
    });
});
