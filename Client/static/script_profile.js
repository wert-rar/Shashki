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

document.addEventListener('DOMContentLoaded', () => {
    createSnowflakes();
});
