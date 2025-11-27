function copyImageURL(url) {
    navigator.clipboard.writeText(url)
        .then(() => {
            const btn = event.target;
            const originalText = btn.innerHTML;
            btn.innerHTML = '✓ Copied!';
            btn.style.background = '#28a745 !important';
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.background = '#1E90FF !important';
            }, 1500);
        })
        .catch(err => {
            console.error("Failed to copy: ", err);
            alert("Failed to copy link");
        });
}

function copyEntryURL(url) {
    navigator.clipboard.writeText(url)
        .then(() => {
            alert("Entry URL copied to clipboard!");
        })
        .catch(err => {
            console.error("Failed to copy: ", err);
        });
}

// CSRF helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie("csrftoken");

document.addEventListener("DOMContentLoaded", function () {
    // ENTRY LIKE AJAX
    const entryLikeForm = document.getElementById("entry-like-form");
    const entryLikeButton = document.getElementById("entry-like-button");
    const entryLikeCount = document.getElementById("entry-like-count");

    if (entryLikeForm && entryLikeButton && entryLikeCount && !entryLikeButton.disabled) {
        entryLikeForm.addEventListener("submit", function (e) {
            e.preventDefault();

            fetch("/api/entries/{{ entry.id }}/like/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrftoken,
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({})
            })
            .then(resp => {
                if (!resp.ok) throw new Error("Failed like");
                return resp.json();
            })
            .then(data => {
            if (typeof data.likes === "number") {
                entryLikeCount.textContent = data.likes;
            }

            entryLikeButton.disabled = true;
            entryLikeButton.textContent = "Liked ✔";
            entryLikeButton.style.cursor = "default";
            entryLikeButton.style.backgroundColor = "#28a745";
            entryLikeButton.onmouseover = function () {
                entryLikeButton.style.backgroundColor = "#28a745";
            };
            entryLikeButton.onmouseout = function () {
                entryLikeButton.style.backgroundColor = "#28a745";
            };

            // refresh "Liked by:" block
            const likesSection = document.getElementById("likes-section");
            if (!likesSection) return;

            fetch("/api/entries/{{ entry.id }}/likes/?size=100", {
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            })
            .then(r => {
                if (!r.ok) throw new Error("Failed to load likes list");
                return r.json();
            })
            .then(json => {
                const items = json.items || json.src || [];
                if (!items.length) {
                    likesSection.innerHTML = "<p>No likes yet.</p>";
                    return;
                }
                const names = items.map(like => {
                    return (like.author && like.author.displayName) || "Unknown";
                });
                likesSection.innerHTML =
                    "<p><strong>Liked by:</strong> " + names.join(", ") + "</p>";
            })
            .catch(err => console.error(err));
        })

        });
    }

    document.querySelectorAll(".comment-like-form").forEach(function (form) {
    const commentId = form.dataset.commentId;
    const button = form.querySelector("button");

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!commentId || !button || button.disabled) return;

        fetch(`/api/comments/${commentId}/like/`, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrftoken,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json",
            },
            body: JSON.stringify({})
        })
        .then(resp => {
            if (!resp.ok) throw new Error("Failed comment like");
            return resp.json();
        })
        .then(data => {
            // Update count on page — just like entry likes
            const countEl = document.getElementById(`comment-like-count-${commentId}`);
            if (countEl && typeof data.likes_count === "number") {
                countEl.textContent = data.likes_count;
            }

            // Update button the same way entry-like does
            button.disabled = true;
            button.textContent = "Liked ✔";
            button.style.cursor = "default";
            button.classList.add("liked-button");

        })
        .catch(err => console.error(err));
    });
});

});