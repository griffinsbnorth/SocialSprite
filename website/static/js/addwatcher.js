$(document).ready(function () {
    //title prefix
    $('#titleprefix').val(watcherdata['titleprefix']);

    //checkboxes
    $('#images').prop('checked', watcherdata['images']);
    $('#tumblr').prop('checked', watcherdata['tumblr']);
    $('#bluesky').prop('checked', watcherdata['bluesky']);
    $('#repost').prop('checked', watcherdata['repost']);
    $('#cycle').prop('checked', watcherdata['cycle']);
    $('#tbhasimages').prop('checked', watcherdata['tbhasimages']);
    $('#bshasimages').prop('checked', watcherdata['bshasimages']);

    //set datepicker
    var scheduledatestring = watcherdata['scheduledate'];
    var cycledatestring = watcherdata['cycledate'];

    var date = new Date();
    date.setUTCDate(date.getUTCDate() + 1);
    if (scheduledatestring != '') {
        var scheddate = new Date(scheduledatestring);
        if (scheddate < date) {
            scheduledatestring = date.toLocaleDateString();
        }
    } else {
        scheduledatestring = date.toLocaleDateString();
    }
    var cycledate = new Date(scheduledatestring);
    cycledate.setUTCDate(cycledate.getUTCDate() + 8);
    if (cycledatestring != '') {
        var cydate = new Date(cycledatestring);
        var scheddate = new Date(scheduledatestring);
        if (cydate < scheddate) {
            cycledatestring = cycledate.toLocaleDateString();
        }
        if (cydate < cycledate) {
            cycledate = cydate;
        }
    } else {
        cycledatestring = cycledate.toLocaleDateString();
    }
    $('#scheduledate').attr('min', date.toLocaleDateString());
    $('#scheduledate').val(scheduledatestring);
    $('#scheduledate').on('change', function () { setCycleMinDate(this.value) });
    $('#cycledate').attr('min', cycledate.toLocaleDateString());
    $('#cycledate').val(cycledatestring);
    $('#time').val(watcherdata['time']);


    //tumblr section
    $('#blogname').val(watcherdata['blogname']);
    $('#ttags').val(watcherdata['ttags']);

    topTagsButton('#topttags', watcherdata['toptbtags'], 'tumblr');
  
    //bluesky section
    topTagsButton('#topbstags', watcherdata['topbstags'], 'bluesky');
    $('#bstags').val(watcherdata['bstags']);

    //form submit
    const form = document.querySelector('form');
    form.addEventListener('formdata', (event) => {
        //this might not be needed
    });

    form.addEventListener('submit', (event) => {
        //check all errors
        var error = false;
        var errormsg = '';
        //to-do: fill later
    });

});

function topTagsButton(tagdiv, tags, tagtype) {
    for (let i = 0; i < tags.length; i++) {
        $(tagdiv).append('<button type="button" onclick="copyPasteTag(\'' + tags[i] + '\', \'' + tagtype +'\')">' + tags[i] + '</button> ');
    }
}

function copyPasteTag(tag, tagtype) {
    if (tagtype == 'tumblr') {
        var oldvalue = $('#ttags').val();
        var newvalue = '';
        if (oldvalue.trim().length > 0) {
            newvalue += ',';
        }
        newvalue += tag;
        $('#ttags').val(oldvalue + newvalue);
    } else {
        var oldvalue = $('#bstags').val();
        var newvalue = '';
        if (oldvalue.trim().length > 0) {
            newvalue += ',';
        }
        newvalue += tag;
        $('#bstags').val(oldvalue + newvalue)
    }
}

//to-do: this'll change when the form is finished
function toggleSection(val, section) {
    const formCheckbox = document.getElementById(val);
    const formSection = document.getElementById(section);
    const submit = document.getElementById('submitBtn');

    formSection.hidden = !formCheckbox.checked;
    if (section == 'imgsection') {
        pond.setOptions({
            required: formCheckbox.checked
        });
    }
    if (section == 'tform') {
        document.getElementById('ttags').required = formCheckbox.checked;
    }

    const tumblrcheck = document.getElementById('tumblr').checked;
    const blueskycheck = document.getElementById('bluesky').checked;
    submit.disabled = !tumblrcheck && !blueskycheck;
};

function setCycleMinDate(date) {
    var cycledate = new Date(date);
    cycledate.setUTCDate(cycledate.getUTCDate() + 8);
    $('#cycledate').attr('min', cycledate.toLocaleDateString());
    var olddate = new Date($('#cycledate').val());
    if (olddate < cycledate) {
        $('#cycledate').val(cycledate.toLocaleDateString());
    }
}

function removeElement(element) {
    var removedElement = document.getElementById(element);
    removedElement.remove();
};
