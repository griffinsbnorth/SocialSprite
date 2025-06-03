$(document).ready(function () {
    //url
    $('#url').val(watcherdata['url']);
    $('#posttext').val(watcherdata['posttext']);
    
    $('#wtype').on('change', function () { changeForm(this.value) });
    $('#wtype').val(watcherdata['wtype']);

    //checkboxes
    $('#images').on('change', function () { toggleSection() });
    $('#tumblr').on('change', function () { toggleSection() });
    $('#bluesky').on('change', function () { toggleSection() });
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

    toggleSection();

    //comic data section
    $('#titleprefix').val(watcherdata['titleprefix']);
    $('#titlekey').val(watcherdata['titlekey']);
    $('#searchkeys').val(watcherdata['searchkeys']);
    $('#updatekey').val(watcherdata['updatekey']);
    $('#prevkey').val(watcherdata['prevkey']);
    $('#nextkey').val(watcherdata['nextkey']);
    $('#slugkey').val(watcherdata['slugkey']);
    $('#archival').on('change', function () { changeForm("comic") });
    $('#archival').prop('checked', watcherdata['archival']);
    $('#pagenum').val(watcherdata['pagenum']);

    changeForm(watcherdata['wtype']);

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

function toggleSection() {
    const imgcheck = document.getElementById('images').checked;
    const tumblrcheck = document.getElementById('tumblr').checked;
    const blueskycheck = document.getElementById('bluesky').checked;
    const tumblrimgcheckdiv = document.getElementById('tbimgpostcheckmark');
    const blueskyimgcheckdiv = document.getElementById('bsimgpostcheckmark');
    const tumblrimgcheck = document.getElementById('tbhasimages').checked;
    const blueskyimgcheck = document.getElementById('bshasimages').checked;
    const submit = document.getElementById('submitBtn');

    tumblrimgcheck.checked = tumblrimgcheck && imgcheck && tumblrcheck
    blueskyimgcheck.checked = blueskyimgcheck && imgcheck && blueskycheck
    tumblrimgcheckdiv.hidden = !imgcheck || !tumblrcheck
    blueskyimgcheckdiv.hidden = !imgcheck || !blueskycheck

    document.getElementById('ttags').required = tumblrcheck
    document.getElementById('bstags').required = blueskycheck
    document.getElementById('tbform').hidden = !tumblrcheck
    document.getElementById('bsform').hidden = !blueskycheck

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

function changeForm(val) {
    const archivalcheck = document.getElementById('archival').checked;
    const iscomic = (val == "comic")
    const isrss = (val == "blog" || val == "youtube")
    document.getElementById('comicform').hidden = !iscomic
    document.getElementById('rssmsg').hidden = !isrss
    document.getElementById('currentcomicmsg').hidden = !(iscomic && !archivalcheck)
    document.getElementById('archivalmsg').hidden = !(iscomic && archivalcheck)
    document.getElementById('titleprefix').required = iscomic
    document.getElementById('titlekey').required = iscomic
    document.getElementById('searchkeys').required = iscomic
    document.getElementById('updatekey').required = iscomic
    document.getElementById('prevkey').required = iscomic
    document.getElementById('nextkey').required = iscomic
}