async function loginUser() {
    const username = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const response = await fetch("http://127.0.0.1:8000/api/token/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: username, password: password })
        });

        const data = await response.json();

        if (response.status === 200) {
            // This puts the key in your pocket
            localStorage.setItem("token", data.access); 
            alert("Login Successful! Access Granted.");
            window.location.href = "/dashboard/";
        } else {
            alert("Invalid Username or Password!");
        }
    } catch (error) {
        console.error(error);
        alert("Server is down!");
    }
}