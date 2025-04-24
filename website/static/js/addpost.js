//error tags
var bsTextError = {};
var tTextError = {};

//post variables
var loaded = false;
var bsPostIndex = 1;
var tBlockIndex = 0;
var richTxtEditors = {};
var bsrichTxtEditors = {};
var bsPhotoSelectors = [];
var tBlocks = [];
var imgthumbnails = {};
var bstoolbarOptions;
var bsoptions;
var bsimagemap = {};
var tbimagemap = {};

var pond;

$(document).ready(function () {
    bsimagemap = postdata['bsimgmap'];
    tbimagemap = postdata['tbimgmap'];
    //title
    $('#title').val(postdata['title']);

    //checkboxes
    $('#images').on('change', function () { toggleSection('images', 'imgsection') });
    $('#tumblr').on('change', function () { toggleSection('tumblr', 'tform') });
    $('#bluesky').on('change', function () { toggleSection('bluesky', 'bsformall') });
    $('#images').prop('checked', postdata['images']);
    $('#tumblr').prop('checked', postdata['tumblr']);
    $('#bluesky').prop('checked', postdata['bluesky']);
    $('#repost').prop('checked', postdata['repost']);
    $('#cycle').prop('checked', postdata['cycle']);

    //set datepicker
    var scheduledatestring = postdata['scheduledate'];
    var cycledatestring = postdata['cycledate'];

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
    $('#time').val(postdata['time']);

    //image section
    // register the plugins with FilePond
    FilePond.registerPlugin(
        FilePondPluginImagePreview,
        FilePondPluginImageResize,
        FilePondPluginImageTransform,
        FilePondPluginFileRename,
        FilePondPluginFileValidateType
    );
    const inputElement = document.getElementById('imgupload');
    pond = FilePond.create(inputElement, {
        allowMultiple: true,
        files: postdata['files'],
        server: {
            load: (source, load) => {
                fetch('/loadfile?source=' + source, {
                    method: "GET"
                }).then(res => res.blob()).then(load);
            }
        },
        imageResizeTargetHeight: 1290,
        imageResizeTargetWidth: 1280,
        imageResizeMode: 'contain',
        imageResizeUpscale: false,
        acceptedFileTypes: ['image/png', 'image/jpeg', 'image/gif', 'image/webp'],
        storeAsFile: true,
        allowReorder: true,
        required: true,
        imageTransformImageFilter: (file) => new Promise(resolve => {

            // no gif mimetype, do transform
            if (!/image\/gif/.test(file.type)) return resolve(true);

            const reader = new FileReader();
            reader.onload = () => {

                var arr = new Uint8Array(reader.result),
                    i, len, length = arr.length, frames = 0;

                // make sure it's a gif (GIF8)
                if (arr[0] !== 0x47 || arr[1] !== 0x49 ||
                    arr[2] !== 0x46 || arr[3] !== 0x38) {
                    // it's not a gif, we can safely transform it
                    resolve(true);
                    return;
                }

                for (i = 0, len = length - 9; i < len, frames < 2; ++i) {
                    if (arr[i] === 0x00 && arr[i + 1] === 0x21 &&
                        arr[i + 2] === 0xF9 && arr[i + 3] === 0x04 &&
                        arr[i + 8] === 0x00 &&
                        (arr[i + 9] === 0x2C || arr[i + 9] === 0x21)) {
                        frames++;
                    }
                }
                // if frame count > 1, it's animated, don't transform
                if (frames > 1) {
                    return resolve(false);
                }
                // do transform
                resolve(true);
            }
            reader.readAsArrayBuffer(file);
        })
    });
    pond.setOptions({
        fileRenameFunction: (file) => {
            var newName = file.name;
            if (file.name == "image.png") {
                newName = 'CPimage_' + Date.now() + `${file.extension}`;
            } else if (file.name in imgthumbnails) {
                newName = file.basename + '_' + Date.now() + `${file.extension}`;
            }
            return newName;
        },
        onaddfile: (error, file) => {
            if (!error) {
                fname = file.filename;
                //$('#watermarks').append('<div id="wm' + fname + '"><label for="watermark' + fname + '"> Add watermark for ' + fname + '? </label><input type="checkbox" id="watermark' + fname + '" name="watermark" value="' + fname + '" ><div/>');
                for (let i = 0; i < bsPhotoSelectors.length; i++) {
                    $(bsPhotoSelectors[i]).append($('<option>', {
                        value: fname,
                        text: fname
                    }));
                }
            }
        },
        onremovefile: (error, file) => {
            if (!error) {
                fname = file.filename;
                removeElement('wm' + fname);
                delete imgthumbnails[fname];
                for (let i = 0; i < bsPhotoSelectors.length; i++) {
                    if ($(bsPhotoSelectors[i]).val() == fname) {
                        $(bsPhotoSelectors[i]).val("none").change();
                    }
                    $(bsPhotoSelectors[i] + " option[value='" + fname + "']").remove();
                }
                for (let i = 0; i < tBlocks.length; i++) {
                    if (tBlocks[i].includes("photo")) {
                        var block = i + 1;
                        if (block in tbimagemap) {
                            let obj = tbimagemap[block].find(o => o === fname);
                            if (obj != null) {
                                let newarray = tbimagemap[block].filter(item => item !== fname);
                                tbimagemap[block] = newarray;
                            }
                        }
                        removeElement('tbthumbb' + block + fname);
                    }
                }
            }
        },
        onpreparefile: (file, output) => {
            fname = file.filename;
            var canvas = document.createElement('canvas');
            canvas.height = 100;
            canvas.width = 200;
            document.getElementById('hiddencanvases').appendChild(canvas);
            var ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            imgthumbnails[fname] = canvas;
            var img = new Image();

            img.onload = function () {
                var scale = 100 / img.height;
                var newwidth = img.width * scale;
                canvas.width = newwidth;
                ctx.drawImage(img, 0, 0, img.width, img.height, 0, 0, newwidth, 100);

                for (let i = 0; i < tBlocks.length; i++) {
                    if (tBlocks[i].includes("photo")) {
                        var block = i + 1;
                        var element = document.getElementById(tBlocks[i]);
                        getImgOptionCheckboxes(tBlocks[i], block);
                    }
                }
                for (const bkey in bsimagemap) {
                    if (bsPhotoSelectors.length >= parseInt(bkey) && bsimagemap[bkey] in imgthumbnails) {
                        $(bsPhotoSelectors[bkey]).val(bsimagemap[bkey]).change();
                        delete bsimagemap[bkey];
                    }
                }
            }

            img.src = URL.createObjectURL(output);
        }
    });

    //tumblr section
    $('#addTbPhotoBtn').click(function () { addTblock('photo') });
    $('#addTbTextBtn').click(function () { addTblock('text') });
    $('#addTbLinkBtn').click(function () { addTblock('link') });
    $('#addTbAudioBtn').click(function () { addTblock('audio') });
    $('#addTbVideoBtn').click(function () { addTblock('video') });
    $('#removeTblockBtn').click(function () { removeTblock() });

    blocks = postdata['blocks'];
    for (let j = 0; j < blocks.length; j++) {
        key = j + 1;
        blocktype = blocks[j]['blocktype'];
        addTblock(blocktype);
        switch (blocktype) {
            case 'text':
                richTxtEditors[key].setContents(blocks[j]['text']);
                break;
            case 'link':
                $('#tblink' + key + 'url').val(blocks[j]['url']);
                break;
            default:
                $('#tb' + blocktype + key + 'url').val(blocks[j]['url']);
                $('#tb' + blocktype + key + 'embed').val(blocks[j]['embed']);
        }
    }
    $('#blogname').val(postdata['blogname']);
    $('#ttags').val(postdata['tags']);

    topTagsButton('#topttags', postdata['toptbtags'], 'tumblr');
    topTagsButton('#topbstags', postdata['topbstags'], 'bluesky');

    //bluesky section
    $('#addBStxtBtn').click(function () { addBStext() });
    $('#removeBStxtBtn').click(function () { removeBStext() });
    $('#bsp1i1').on('change', function () { addThumbnail(this.value, this) });
    $('#bsp1i2').on('change', function () { addThumbnail(this.value, this) });
    $('#bsp1i3').on('change', function () { addThumbnail(this.value, this) });
    $('#bsp1i4').on('change', function () { addThumbnail(this.value, this) });
    bsPhotoSelectors[0] = '#bsp1i1';
    bsPhotoSelectors[1] = '#bsp1i2';
    bsPhotoSelectors[2] = '#bsp1i3';
    bsPhotoSelectors[3] = '#bsp1i4';


    bstoolbarOptions = [
        ['link'],        // toggled buttons
        ['clean']        // remove formatting button
    ];
    bsoptions = {
        modules: {
            toolbar: bstoolbarOptions,
        },
        theme: 'snow'
    };
    bsrichTxtEditors[1] = new Quill('#bstext1', bsoptions);
    bsrichTxtEditors[1].on('text-change', (delta, oldDelta, source) => {
        countChar(1, '#charNum1');
    });
    bsTextError[1] = false;
    skeets = postdata['skeets'];
    for (let i = 0; i < skeets.length; i++) {
        key = i + 1;
        if (!(key in bsrichTxtEditors)) {
            addBStext();
        }
        bsrichTxtEditors[key].setContents(skeets[i]);
    }

    toggleSection('images', 'imgsection');
    toggleSection('tumblr', 'tform');
    toggleSection('bluesky', 'bsformall');

    //form submit
    const form = document.querySelector('form');
    form.addEventListener('formdata', (event) => {
        // Append Quill content before submitting
        for (const key in richTxtEditors) {
            event.formData.append('tbtext' + key, JSON.stringify(richTxtEditors[key].getContents().ops));
        }
        for (const key in bsrichTxtEditors) {
            event.formData.append('bstext' + key, JSON.stringify(bsrichTxtEditors[key].getContents().ops));
        }
        var pondfiles = pond.getFiles();
        var pondfilelist = {};
        for (let i = 0; i < pondfiles.length; i++) {
            var fname = pondfiles[i].filename;
            pondfilelist[fname] = i;
        }
        event.formData.append('fileorder', JSON.stringify(pondfilelist));
        event.formData.append('bsskeetlen', bsPostIndex);
    });

    form.addEventListener('submit', (event) => {
        //check all errors
        var error = false;
        var errormsg = '';
        var tumblrattachedimages = false;
        var blueskyattachedimages = false;
        var photoblocks = 0;
        if ($('#tumblr').is(':checked')) {
            if (tBlockIndex > 0) {
                for (const key in richTxtEditors) {
                    if (richTxtEditors[key].getText().trim().length == 0) {
                        errormsg += 'Tumblr block #' + key + ' can\'t be empty.</br>';
                        error = true;
                    }
                }
                for (let i = 0; i < tBlocks.length; i++) {
                    var block = i + 1;
                    if (tBlocks[i].includes("photo")) {
                        photoblocks += 1;
                        var imgcheckboxes = document.getElementsByName("imgcheckbox" + block);
                        var checked = false;
                        for (let j = 0; j < imgcheckboxes.length; j++) {
                            checked = checked || imgcheckboxes[j].checked;
                        }
                        if (!checked) {
                            errormsg += 'Tumblr photo block #' + block + ' has no chosen photos.</br>';
                            error = true;
                        }
                        tumblrattachedimages = tumblrattachedimages || checked;
                    } else if (tBlocks[i].includes("text")) {
                        if (tTextError[block]) {
                            errormsg += 'Tumblr text block #' + block + ' is over the character limit.</br>';
                            error = true;
                        }
                    }
                }
                $('#tbhasimages').prop('checked', tumblrattachedimages);
            } else {
                errormsg += 'Tumblr post can\'t be empty.</br>';
                error = true;
            }
        }
        if ($('#bluesky').is(':checked')) {
            for (const key in bsTextError) {
                if (bsTextError[key]) {
                    errormsg += 'Skeet #' + key + ' is over the character limit.</br>';
                    error = true;
                }
            }
            for (const key in bsrichTxtEditors) {
                if (bsrichTxtEditors[key].getText().trim().length == 0) {
                    errormsg += 'Skeet #' + key + ' can\'t be empty.</br>';
                    error = true;
                }
            }
            for (let i = 0; i < bsPhotoSelectors.length; i++) {
                if ($(bsPhotoSelectors[i]).val() != "none") {
                    blueskyattachedimages = true;
                }
            }
            $('#bshasimages').prop('checked', blueskyattachedimages);
        }
        if ($('#images').is(':checked') && !blueskyattachedimages && !tumblrattachedimages) {
            errormsg += 'Image post has no images attached to post or skeet(s)</br>';
            error = true;
        }
        if (!$('#images').is(':checked') && $('#tumblr').is(':checked') && photoblocks == tBlocks.length) {
            errormsg += 'Tumblr post cannot consist of only photo blocks if there are no images</br>';
            error = true;
        }


        if (error) {
            $('#errormessages').html(errormsg);
            event.preventDefault();
            return false;
        }
    });

    loaded = true;
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
        var len = bsrichTxtEditors[1].getText().length - 1;
        bsrichTxtEditors[1].insertText(len, ' #' + tag);
    }
}

function addImgOptions(dropdown) {
    dropdown.innerHTML = '<option value="none">None</option>';
    for (const key in imgthumbnails) {
        dropdown.innerHTML += '<option value="' + key + '">' + key + '</option>';
    }
};

function addThumbnail(option, thumb) {
    const thumbnail = thumb.previousElementSibling;
    if (option != "none" && option in imgthumbnails) {
        thumbnail.hidden = false;
        thumbnail.src = imgthumbnails[option].toDataURL();
    } else {
        thumbnail.hidden = true;
    }
};

function getImgOptionCheckboxes(elementname, order) {
    const element = document.getElementById(elementname);
    element.innerHTML = '';

    for (const key in imgthumbnails) {
        var newHTML = '<div id="tbthumbb' + order + key + '" class="tbthumbcontainer">';
        newHTML += '<img class="bsImgThmb" src="' + imgthumbnails[key].toDataURL() + '">';
        newHTML += '<input type="checkbox" id="tb' + order + key + '" name="imgcheckbox' + order + '" value="' + key + '" onchange="toggleImgOptionCheckbox(this, ' + order + ')">'
        newHTML += '<label for="tb' + order + key + '">' + key + '</label></div><br>';
        element.innerHTML += newHTML;
        if (order in tbimagemap) {
            let obj = tbimagemap[order].find(o => o === key);
            if (obj != null) {
                var imgcheckbox = document.getElementById('tb' + order + key);
                imgcheckbox.setAttribute("checked", "checked");
            }
        }
    }
};

function toggleImgOptionCheckbox(element, order) {
    if (element.checked) {
        if (order in tbimagemap) {
            tbimagemap[order].push(element.value);
        } else {
            tbimagemap[order] = [element.value];
        }
    } else {
        let obj = tbimagemap[order].find(o => o === element.value);
        if (obj != null) {
            let newarray = tbimagemap[order].filter(item => item !== element.value);
            tbimagemap[order] = newarray;
        }
    }
}

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

function countChar(index, counter) {
    var len = bsrichTxtEditors[index].getText().trim().length;
    if (len > 300) {
        $(counter).css('color', 'red');
        bsTextError[index] = true;
    } else {
        $(counter).css('color', 'black');
        bsTextError[index] = false;
    }
    $(counter).text(len + '/300');
};

function countTbChar(index, counter) {
    var len = richTxtEditors[index].getText().trim().length;
    if (len > 4096) {
        $(counter).css('color', 'red');
        tTextError[index] = true;
    } else {
        $(counter).css('color', 'black');
        tTextError[index] = false;
    }
    $(counter).text(len + '/4096');
};

function removeElement(element) {
    var removedElement = document.getElementById(element);
    removedElement.remove();
};

function addBStext() {
    bsPostIndex += 1;
    $('#removeBStxtBtn').removeAttr('hidden');
    $('#bsform').append('<div id="bspost' + bsPostIndex + '" name="bspost"></div>');
    $('#bspost' + bsPostIndex).append('<div class="bsimgselectcontainer" id="bsimgselectcontainer' + bsPostIndex + '"></div>');
    for (i = 1; i < 5; i++) {
        $('#bsimgselectcontainer' + bsPostIndex).append('<div name="bsimgselect" id="bsimgselectp' + bsPostIndex + 'i' + i + '" class="bsimgselect"></div>');
        $('#bsimgselectp' + bsPostIndex + 'i' + i).append('<img class="bsImgThmb" src="" id="bsp' + bsPostIndex + 'i' + i + 'thmb" hidden />');
        $('#bsimgselectp' + bsPostIndex + 'i' + i).append('<select name="bsimgs" id="bsp' + bsPostIndex + 'i' + i + '"><option value="none" selected>None</option></select>');
        var thumbnail = 'bsp' + bsPostIndex + 'i' + i + 'thmb';
        $('#bsp' + bsPostIndex + 'i' + i).on('change', function () { addThumbnail(this.value, this) });
        addImgOptions(document.getElementById('bsp' + bsPostIndex + 'i' + i));
        bsPhotoSelectors.push('#bsp' + bsPostIndex + 'i' + i);
    }
    $('#bspost' + bsPostIndex).append('<div id="bstext' + bsPostIndex + '" name="bstext"></div>');
    bsrichTxtEditors[bsPostIndex] = new Quill('#bstext' + bsPostIndex, bsoptions);
    bsrichTxtEditors[bsPostIndex].on('text-change', (delta, oldDelta, source) => {
        countChar(bsPostIndex, '#charNum' + bsPostIndex);
    });
    $('#bspost' + bsPostIndex).append('<div id="charNum' + bsPostIndex + '" class="charNum">0/300</div>');
};

function removeBStext() {
    for (i = 1; i < 5; i++) {
        bsPhotoSelectors.pop();
    }
    removeElement('bspost' + bsPostIndex);
    delete bsrichTxtEditors[bsPostIndex];
    bsPostIndex -= 1;
    if (bsPostIndex == 1) {
        $('#removeBStxtBtn').prop('hidden', true);
    }
};

function addTblock(blocktype) {
    tBlockIndex += 1;
    $('#removeTblockBtn').removeAttr('hidden');
    $('#tblocks').append('<div id="tblock' + tBlockIndex + '" name="tblock" class="tblock"></div>');
    $('#tblock' + tBlockIndex).append('<h4>' + blocktype.toUpperCase() + '</h4>');
    $('#tblock' + tBlockIndex).append('<input type="text" id="tbtype' + tBlockIndex + '" name="tbtype" hidden>');
    $('#tbtype' + tBlockIndex).val(blocktype + ':' + tBlockIndex);
    tBlocks.push('tb' + blocktype + tBlockIndex);


    switch (blocktype) {
        case "text":
            $('#tblock' + tBlockIndex).append('<div id="tbtext' + tBlockIndex + '" name="tbtext"></div>');
            const toolbarOptions = [
                ['bold', 'italic', 'underline', 'strike', 'link'],        // toggled buttons

                [{ 'color': [] }],
                [{ 'list': 'ordered' }, { 'list': 'bullet' }],
                [{ 'header': [1, 2, false] }],

                ['clean']                                         // remove formatting button
            ];
            const options = {
                modules: {
                    toolbar: toolbarOptions,
                },
                theme: 'snow'
            };
            $('#tblock' + tBlockIndex).append('<div id="tbcharNum' + tBlockIndex + '" class="tbcharNum">0/4096</div>');
            richTxtEditors[tBlockIndex] = new Quill('#tbtext' + tBlockIndex, options);
            let i = tBlockIndex;
            richTxtEditors[tBlockIndex].on('text-change', (delta, oldDelta, source) => {
                countTbChar(i, '#tbcharNum' + i);
            });
            break;
        case "photo":
            $('#tblock' + tBlockIndex).append('<div id="tbphoto' + tBlockIndex + '" name="tbphoto' + tBlockIndex + '" class="tbphoto"></div>');
            getImgOptionCheckboxes('tbphoto' + tBlockIndex, tBlockIndex);
            break;
        case "link":
            $('#tblock' + tBlockIndex).append('<label for="tblink' + tBlockIndex + 'url">url:</label><input type="url" id="tblink' + tBlockIndex + 'url" name="tblink' + tBlockIndex + 'url" placeholder="https:\/\/example.com\/" class="form-control" required>');
            break;
        case "audio":
            $('#tblock' + tBlockIndex).append('<label for="tbaudio' + tBlockIndex + 'url">url:</label><input type="url" id="tbaudio' + tBlockIndex + 'url" name="tbaudio' + tBlockIndex + 'url" placeholder="https:\/\/example.com\/" class="form-control" required>');
            $('#tblock' + tBlockIndex).append('<label for="tbaudio' + tBlockIndex + 'embed">Embed HTML Code:</label><input type="text" id="tbaudio' + tBlockIndex + 'embed" name="tbaudio' + tBlockIndex + 'embed" class="form-control">');
            break;
        case "video":
            $('#tblock' + tBlockIndex).append('<label for="tbvideo' + tBlockIndex + 'url">url:</label><input type="url" id="tbvideo' + tBlockIndex + 'url" name="tbvideo' + tBlockIndex + 'url" placeholder="https:\/\/example.com\/" class="form-control" required>');
            $('#tblock' + tBlockIndex).append('<label for="tbvideo' + tBlockIndex + 'embed">Embed HTML Code:</label><input type="text" id="tbvideo' + tBlockIndex + 'embed" name="tbvideo' + tBlockIndex + 'embed" class="form-control">');
    }
};

function removeTblock() {
    tBlocks.pop();
    removeElement('tblock' + tBlockIndex);
    if (richTxtEditors[tBlockIndex] != null) {
        delete richTxtEditors[tBlockIndex];
    }
    tBlockIndex -= 1;
    if (tBlockIndex == 0) {
        $('#removeTblockBtn').prop('hidden', true);
    }
};

