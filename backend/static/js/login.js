async function loginUser() {
    const username = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const response = await fetch("http://127.0.0.1:8000/api/token/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (response.status === 200) {
            localStorage.setItem("token", data.access);
            alert("Login successful");
            window.location.href = "/dashboard/";
        } else {
            alert("Invalid username or password");
        }

    } catch (error) {
        console.error(error);
        alert("Something went wrong");
    }
}