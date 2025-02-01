function updateDateTime() {
    const now = new Date();
    const timeElement = document.getElementById('current-time');
    const dateElement = document.getElementById('current-date');
    
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    };
    
    dateElement.textContent = now.toLocaleDateString('en-US', options);
    timeElement.textContent = now.toLocaleTimeString('en-US');
}

// Update time every second
setInterval(updateDateTime, 1000);

// Initial call
updateDateTime();
