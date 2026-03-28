(function() {
    const token = localStorage.getItem("token");

    if (!token) {
        // If the HTML script missed it, the JS will catch it here
        window.location.replace("/login/");
        return;
    }

    document.addEventListener("DOMContentLoaded", function () {
        fetch("http://127.0.0.1:8000/api/dashboard/", {
            method: "GET",
            headers: {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json"
            }
        })
        .then(response => {
            if (!response.ok) {
                localStorage.clear();
                window.location.replace("/login/");
            }
            return response.json();
        })
        .then(data => {
            // Update your UI counts here
            if(document.getElementById("electriciansCount")) {
                document.getElementById("electriciansCount").innerText = data.electricians.length;
            }
        })
        .catch(error => {
            console.error("Error:", error);
            window.location.replace("/login/");
        });
    });
})();