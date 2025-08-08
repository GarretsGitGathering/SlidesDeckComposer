const API_BASE_URL = "https://luke-ai-slides-deck-project-z089.onrender.com";   // https://luke-ai-slides-deck-project.onrender.com

// Function to categorize presentations by IDs
async function categorizePresentations() {
    const presentationIdsInput = document.getElementById("presentation-ids").value;
    const messageElement = document.getElementById("categorize-message");

    if (!presentationIdsInput) {
        messageElement.textContent = "Please enter presentation IDs.";
        messageElement.classList.add("error");
        return;
    }

    const presentationIds = presentationIdsInput.split(",").map(id => id.trim());

    try {
        const response = await fetch(`${API_BASE_URL}/categorize_presentations`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ presentation_ids: presentationIds })
        });

        const result = await response.json();
        if (response.ok) {
            messageElement.textContent = result.message;
            messageElement.classList.remove("error");
        } else {
            messageElement.textContent = result.error || "An error occurred.";
            messageElement.classList.add("error");
        }
    } catch (error) {
        messageElement.textContent = "Failed to connect to the server.";
        messageElement.classList.add("error");
    }
}

// Function to toggle input fields based on selection
function toggleBackgroundInput() {
    const backgroundType = document.getElementById("background-type").value;
    const colorInputGroup = document.getElementById("color-input-group");
    const imageInputGroup = document.getElementById("image-input-group");

    // Show/hide input fields based on the selected option
    if (backgroundType === "color") {
        colorInputGroup.style.display = "block";
        imageInputGroup.style.display = "none";
    } else if (backgroundType === "image") {
        colorInputGroup.style.display = "none";
        imageInputGroup.style.display = "block";
    } else {
        colorInputGroup.style.display = "none";
        imageInputGroup.style.display = "none";
    }
}

// Function to create a new presentation
async function createPresentation() {
    const clientIntent = document.getElementById("client-intent").value;
    const title = document.getElementById("presentation-title").value;
    const backgroundType = document.getElementById("background-type").value;
    const backgroundColor = backgroundType === "color" ? document.getElementById("background-color").value : null;
    const backgroundImageUrl = backgroundType === "image" ? document.getElementById("background-image-url").value.trim() : null;
    //const themeTemplateId = backgroundType === "theme" ? document.getElementById("theme-template-id").value.trim() : null;
    const messageElement = document.getElementById("create-message");

    if (!clientIntent || !title) {
        messageElement.textContent = "Please enter both client intent and presentation title.";
        messageElement.classList.add("error");
        return;
    }

    if ((backgroundColor && backgroundImageUrl)) {
        messageElement.textContent = "Please provide only one background option or theme.";
        messageElement.classList.add("error");
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/generate_presentation`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                client_intent: clientIntent,
                title: title,
                layout_id: "your-default-layout-id",  // Replace with the default or user-selected layout ID
                background_color: backgroundColor || null,
                background_image_url: backgroundImageUrl || null,
                //theme_template_id: themeTemplateId || null
            })
        });

        const result = await response.json();
        if (response.ok) {
            messageElement.textContent = result.message;
            messageElement.classList.remove("error");
        } else {
            messageElement.textContent = result.error || "An error occurred.";
            messageElement.classList.add("error");
        }
    } catch (error) {
        messageElement.textContent = "Failed to connect to the server.";
        messageElement.classList.add("error");
    }
}


// Function to categorize presentations by type
async function categorizePresentationsByType() {
    const typeInput = document.getElementById("presentation-type").value;
    const messageElement = document.getElementById("categorize-type-message");

    if (!typeInput) {
        messageElement.textContent = "Please enter a presentation type.";
        messageElement.classList.add("error");
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/categorize_presentations_by_type`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ type: typeInput })
        });

        const result = await response.json();
        if (response.ok) {
            messageElement.textContent = result.message;
            messageElement.classList.remove("error");
        } else {
            messageElement.textContent = result.error || "An error occurred.";
            messageElement.classList.add("error");
        }
    } catch (error) {
        messageElement.textContent = "Failed to connect to the server.";
        messageElement.classList.add("error");
    }
}

// Function to refresh the token
async function refreshToken() {
    const messageElement = document.getElementById("refresh-message");

    try {
        const response = await fetch(`${API_BASE_URL}/refresh_token`, {
            method: "GET"
        });

        const result = await response.json();
        if (response.ok) {
            if (result.status === "login_required") {
                // Redirect the user to the Google sign-in page
                window.location.href = result.auth_url;
            } else {
                messageElement.textContent = result.message;
                messageElement.classList.remove("error");
            }
        } else {
            messageElement.textContent = result.error || "An error occurred.";
            messageElement.classList.add("error");
        }
    } catch (error) {
        messageElement.textContent = "Failed to connect to the server.";
        messageElement.classList.add("error");
    }
}

// Function to upload and replace credentials
async function uploadCredentials() {
    const fileInput = document.getElementById("file-input");
    const uploadMessage = document.getElementById("upload-message");

    if (fileInput.files.length === 0) {
        uploadMessage.textContent = "No file selected.";
        uploadMessage.classList.add("error");
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${API_BASE_URL}/upload_credentials`, {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        if (response.ok) {
            uploadMessage.textContent = "Credentials uploaded successfully.";
            uploadMessage.classList.remove("error");
        } else {
            uploadMessage.textContent = result.error || "An error occurred.";
            uploadMessage.classList.add("error");
        }
    } catch (error) {
        uploadMessage.textContent = "Failed to upload credentials.";
        uploadMessage.classList.add("error");
    }
}