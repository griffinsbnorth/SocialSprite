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

    //schedule data
    $('#month').val(watcherdata['scheduledata']['month']);
    $('#day_of_month').val(watcherdata['scheduledata']['day_of_month']);
    $('#hour').val(watcherdata['scheduledata']['hour']);
    $('#minute').val(watcherdata['scheduledata']['minute']);
    const days_of_week = document.getElementsByName('day_of_week');
    Array.from(days_of_week).forEach((day_of_week, index) => {
        day_of_week.checked = watcherdata['scheduledata']['day_of_week'].includes(day_of_week.value);
    });

    //cycle weeks
    $('#weeks').val(watcherdata['cycleweeks']);

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
        const imgchkbox = document.getElementById('images');
        if (imgchkbox.disabled) {
            imgchkbox.disabled = false;
            if (imgchkbox.checked) {
                event.formData.append('images', 'images');
            }
        }
    });

    form.addEventListener('submit', (event) => {

        //check all errors
        var error = false;
        var errormsg = '';
        const watchertype = $('#wtype').val()

        const month_is_empty = $('#month').val() == 0
        const day_of_month_is_empty = $('#day_of_month').val() == 0
        const hour_is_empty = $('#hour').val()  == -1
        const minute_is_empty = $('#minute').val() == -1
        var day_of_week_is_nonempty = false
        const days_of_week = document.getElementsByName('day_of_week');
        Array.from(days_of_week).forEach((day_of_week, index) => {
            if (day_of_week.checked == true) {
                day_of_week_is_nonempty = true;
            }
        });
        if (month_is_empty && day_of_month_is_empty && hour_is_empty && minute_is_empty && !day_of_week_is_nonempty) {
            errormsg += 'At least one schedule behaviour must be chosen.</br>';
            error = true;
        }

        if ($('#cycle').is(':checked')) {
            const weeks_is_empty = $('#weeks').val() == 0
            if (weeks_is_empty) {
                errormsg += 'Missing cycle data.</br>';
                error = true;
            }
        }

        if (!$('#tumblr').is(':checked') && !$('#bluesky').is(':checked')) {
            errormsg += 'No social media selected for post generation.</br>';
            error = true;
        }

        if ($('#images').is(':checked') && !$('#tbhasimages').is(':checked') && !$('#bshasimages').is(':checked')) {
            errormsg += 'Images is selected but no social media was selected to add images to.</br>';
            error = true;
        }

        if (watchertype == "comic") {
            if ($('#archival').is(':checked') ){

                if ($('#pagenum').val() == 0) {
                    errormsg += 'Pages per update can\'t be empty if archival.</br>';
                    error = true;
                }
            }
            if ($('#titlekey').val() == "slug") {
                if ($('#slugkey').val() == '') {
                    errormsg += 'Slug key can\'t be empty if titlekey is "slug".</br>';
                    error = true;
                }
            }
        }

        if (error) {
            $('#errormessages').html(errormsg);
            event.preventDefault();
            return false;
        }
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
    document.getElementById('tbhasimages').disabled = !imgcheck || !tumblrcheck
    document.getElementById('bshasimages').disabled = !imgcheck || !blueskycheck
    tumblrimgcheckdiv.hidden = !imgcheck || !tumblrcheck
    blueskyimgcheckdiv.hidden = !imgcheck || !blueskycheck

    document.getElementById('ttags').required = tumblrcheck
    document.getElementById('bstags').required = blueskycheck
    document.getElementById('tbform').hidden = !tumblrcheck
    document.getElementById('bsform').hidden = !blueskycheck

    submit.disabled = !tumblrcheck && !blueskycheck;
};

function removeElement(element) {
    var removedElement = document.getElementById(element);
    removedElement.remove();
};

function changeForm(val) {
    const archivalcheck = document.getElementById('archival').checked;
    const iscomic = (val == "comic");
    const isrss = (val == "blog" || val == "youtube");
    const imgchkbox = document.getElementById('images');
    const repostchkbox = document.getElementById('repost');
    const cyclechkbox = document.getElementById('cycle');
    document.getElementById('comicform').hidden = !iscomic;
    document.getElementById('rssmsg').hidden = !isrss
    document.getElementById('currentcomicmsg').hidden = !(iscomic && !archivalcheck);
    document.getElementById('archivalmsg').hidden = !(iscomic && archivalcheck);
    document.getElementById('titleprefix').required = iscomic;
    document.getElementById('titlekey').required = iscomic;
    document.getElementById('searchkeys').required = iscomic;
    document.getElementById('updatekey').required = iscomic;
    document.getElementById('prevkey').required = iscomic;
    document.getElementById('nextkey').required = iscomic;
    if (iscomic) {
        imgchkbox.checked = true
        toggleSection()
        imgchkbox.disabled = true
        cyclechkbox.disabled = false
        repostchkbox.disabled = false
    } else if (val == "youtube") {
        imgchkbox.checked = false
        imgchkbox.disabled = true
        cyclechkbox.disabled = false
        repostchkbox.disabled = false
        toggleSection()
    } else if (val == "twitch") {
        imgchkbox.checked = false
        imgchkbox.disabled = true
        repostchkbox.checked = false
        repostchkbox.disabled = true
        cyclechkbox.checked = false
        cyclechkbox.disabled = true
        toggleSection()
    } else {
        imgchkbox.disabled = false
        cyclechkbox.disabled = false
        repostchkbox.disabled = false
    }
}