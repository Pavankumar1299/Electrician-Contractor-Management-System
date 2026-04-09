document.addEventListener("DOMContentLoaded", function () {

    fetch("http://127.0.0.1:8000/api/dashboard/")
        // .then(response => response.text())
        .then(response => response.json())
        .then(data => {

            // console.log("RAW API RESPONSE:", data);
            // Safely get the lengths. If the array doesn't exist, it defaults to an empty array [] so .length just safely returns 0.
            const electriciansCount = (data.electricians || []).length;
            const jobsCount = (data.jobs || []).length;
            const tasksCount = (data.tasks || []).length;
        
            // If you have placeholders for future features, safely set them to 0 for now
            const materialsCount = (data.materials || []).length;

            // Total electricians
            document.getElementById("electriciansCount").innerText = electriciansCount;

            // Total jobs
            document.getElementById("jobsCount").innerText = jobsCount;

            // Pending tasks
            const pendingTasks = data.tasks.filter(task => task.status === "pending");
            document.getElementById("tasksCount").innerText = pendingTasks.length;

            // Completed tasks
            const completedTasks = data.tasks.filter(task => task.status === "completed");
            document.getElementById("completedCount").innerText = completedTasks.length;

        })
        .catch(error => {
            console.error("Error:", error);
        });

});