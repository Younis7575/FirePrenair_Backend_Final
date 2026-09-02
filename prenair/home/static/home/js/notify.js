const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';

const socket = new WebSocket(`${wsProtocol}${window.location.host}/ws/notifications/`);

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    showNotificationMessage(data.message, "info"); 
    playNotificationSound();
    updateTitleWithRedDot();
};

function showNotificationMessage(message, type = "info") {
    const messagesContainer = document.querySelector('.messages');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        ${message}
        <span class="close-icon" aria-label="Close" title="Close">&times;</span>
    `;

    alert.querySelector('.close-icon').addEventListener('click', () => {
        alert.style.animation = 'fadeOut 0.5s forwards';

        alert.addEventListener('animationend', () => {
            alert.remove();
        });
    });

    messagesContainer.appendChild(alert);
}


function playNotificationSound() {
    const audio = new Audio('https://fireprenair.s3.amazonaws.com/images/misc/sound.wav');
    audio.play();
}


    function updateTitleWithRedDot() {
        if (!document.title.startsWith('🔴')) {
            document.title = `• ${document.title}`;
        }
    }
