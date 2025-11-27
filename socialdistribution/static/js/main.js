//for stream.html show full post content
function toggleContent(elementId, lineLimit) {
    const content = document.getElementById(elementId);
    const button = document.getElementById(`${elementId}-button`);

    if (content.classList.contains("expanded")) {
        // Collapse the content
        content.classList.remove("expanded");
        content.classList.add(`line-clamp-${lineLimit}`); // Reapply the line limit
        button.innerHTML = "..."; // Change button text to "Read More"
    } else {
        // Expand the content
        content.classList.add("expanded");
        content.classList.remove(`line-clamp-${lineLimit}`); // Remove the line limit
        button.innerHTML = "..."; // Change button text to "Show Less"
    }
}


