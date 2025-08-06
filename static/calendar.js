document.addEventListener('DOMContentLoaded', function () {
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'fr',
        events: '/api/paiements',
        eventClick: function (info) {
            alert('Paiement : ' + info.event.title + '\nDate : ' + info.event.start.toLocaleDateString());
        }
    });
    calendar.render();
});
