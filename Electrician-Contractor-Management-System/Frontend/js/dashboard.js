document.addEventListener("DOMContentLoaded", function () {

    fetch("http://127.0.0.1:8000/dashboard/")
        .then(response => response.json())
        .then(data => {

            // Total electricians
            document.getElementById("electriciansCount").innerText = data.electricians.length;

            // Total jobs
            document.getElementById("jobsCount").innerText = data.jobs.length;

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