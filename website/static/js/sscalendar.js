"use strict";

var calendar, organizer;

$(document).ready(function () {
    //https://github.com/nizarmah/calendar-javascript-lib
    calendar = new Calendar("calendarContainer",         // HTML container ID,                                             Required
        "medium",                     // Size: (small, medium, large)                                                           Required
        ["Sunday", 3],               // [ Starting day, day abbreviation length ]                                              Required
        ["#ffc107",                 // Primary Color                                                                           Required
         "#ffa000",                 // Primary Dark Color                                                                      Required
         "#ffffff",                 // Text Color                                                                              Required
         "#ffecb3"],               // Text Dark Color                                                                          Required
        { // Following is optional
            days: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
            months: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
            indicator: true,         // Day Event Indicator                                                                    Optional
            indicator_type: 1,       // Day Event Indicator Type (0 not to display num of events, 1 to display num of events)  Optional
            indicator_pos: "bottom", // Day Event Indicator Position (top, bottom)                                             Optional
            placeholder: "<span>Nothing scheduled.</span>"
        });

    organizer = new Organizer("organizerContainer", calendar, events);

    organizer.onMonthChange = function (callback) {
        let year = calendar.date.getFullYear();
        let month = calendar.date.getMonth() + 1; //count is off by 1 for some reason
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function () {
            if (this.readyState == 4 && this.status == 200) {
                const serverdata = JSON.parse(this.responseText);

                try {
                    organizer.data = serverdata;
                } catch (e) {
                    console.log(e)
                }
                callback();
            }
        };
        xhttp.open("GET", "loadmonth?year=" + year + "&month=" + month, true);
        xhttp.send();
    };

});