document.addEventListener("DOMContentLoaded", function() {

    //-------------------------------------- Comment dropdown -------------------------------
    document.querySelectorAll('.comment-toggle-btn').forEach((button) => {
        button.addEventListener('click', () => {
            const postCard = button.closest('.post-single-box');
            const commentsArea = postCard.querySelector('.post-comments');

            // Check if commentsArea is found
            if (commentsArea) {
                console.log(commentsArea.style.display)
                commentsArea.style.display = (commentsArea.style.display === 'none' || !commentsArea.style.display) ? 'block' : 'none';
            }
        });
    });
});

// ----------------------------------- Like Functionality -----------------------------
function toggleLike(slug, csrf_token) {
    fetch(`/commuprenair/like/${slug}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrf_token,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ slug: slug })
    })
        .then(response => response.json())
        .then(data => {
            const likeIcon = document.getElementById(`like-icon-${slug}`);
            const likeText = document.getElementById(`like-text-${slug}`);
            const likeList = document.getElementById(`like-list-${slug}`);
            const likeCount = document.getElementById(`like-count-${slug}`);

            // Update UI to show liked or unliked state
            if (data.liked) {
                likeIcon.textContent = 'favorite';
                likeIcon.style.color = 'red';
                likeText.textContent = 'Liked';
            } else {
                likeIcon.textContent = 'favorite_border';
                likeIcon.style.color = 'black';
                likeText.textContent = 'Like';
            }

            likeCount.textContent = `${data.like_count}+`;

            likeList.innerHTML = '';

            data.liked_users.forEach(user => {
                const userListItem = document.createElement('li');
                userListItem.id = `like-user-${user.slug}`;
                userListItem.innerHTML = `<img src="${user.profile_pic}" alt="image">`;
                likeList.appendChild(userListItem);
            });

            const likeCountListItem = document.createElement('li');
            likeCountListItem.appendChild(likeCount); // Append the existing count element
            likeList.appendChild(likeCountListItem);

            likeCount.addEventListener('click', () => showLikesPopup(slug));
            likeList.addEventListener('click', () => showLikesPopup(slug));
        })
        .catch(error => console.error('Error:', error));
}

function showLikesPopup(slug) {
    const popup = document.getElementById('like-popup');
    const usersList = document.getElementById('like-users-list');

    fetch(`/commuprenair/likes/${slug}/`)
        .then(response => response.json())
        .then(data => {
    
            usersList.innerHTML = '';

            // Populate list with users
            data.liked_users.forEach(user => {
                const listItem = document.createElement('li');
                listItem.innerHTML = `<a href="/commuprenair/profile/${user.slug}"><img src="${user.profile_pic}" alt="${user.name}"> ${user.name}</a>`;
                usersList.appendChild(listItem);
            });
        });

    // Show popup
    popup.style.display = 'flex';
}

function closePopup() {
    const popup = document.getElementById('like-popup');
    popup.style.display = 'none';
}