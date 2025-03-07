//error tags
var bsTextError = {};
var tTextError = {};

//post variables
var bsPostIndex = 1;
var tBlockIndex = 0;
var richTxtEditors = {};
var bsrichTxtEditors = {};
var bsPhotoSelectors = [];
var tBlocks = [];
var imgthumbnails = {};
var bstoolbarOptions;
var bsoptions;

var pond;

$(document).ready(function () {
    //checkboxes
    $('#images').on('change', function () { toggleSection('images', 'imgsection') });
    $('#tumblr').on('change', function () { toggleSection('tumblr', 'tform') });
    $('#bluesky').on('change', function () { toggleSection('bluesky', 'bsform') });

    //set datepicker
    var date = new Date();
    date.setUTCDate(date.getUTCDate() + 1);
    var cycledate = new Date();
    cycledate.setUTCDate(cycledate.getUTCDate() + 8);
    $('#scheduledate').attr('min', date.toLocaleDateString());
    $('#scheduledate').on('change', function () { setCycleMinDate(this.value) });
    $('#cycledate').attr('min', cycledate.toLocaleDateString());
    $('#cycledate').val(cycledate.toLocaleDateString());

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
        imageResizeTargetHeight: 1290,
        imageResizeTargetWidth: 1280,
        imageResizeMode: 'contain',
        imageResizeUpscale: false,
        acceptedFileTypes: ['image/png', 'image/jpeg', 'image/gif', 'image/webp'],
        storeAsFile: true,
        allowReorder: true,
        required: true
    });
    pond.setOptions({
        fileRenameFunction: (file) => {
            var newName = file.name;
            if (file.name == "image.png") {
                newName = 'CPimage_' + Date.now() + `${file.extension}`;
            }
            return newName;
        },
        onaddfile: (error, file) => {
            if (!error) {
                $('#watermarks').append('<div id="wm' + file.filename + '"><label for="watermark' + file.filename + '"> Add watermark for ' + file.filename + '? </label><input type="checkbox" id="watermark' + file.filename + '" name="watermark" value="' + file.filename + '" ><div/>');
                for (let i = 0; i < bsPhotoSelectors.length; i++) {
                    $(bsPhotoSelectors[i]).append($('<option>', {
                        value: file.filename,
                        text: file.filename
                    }));
                }
            }
        },
        onremovefile: (error, file) => {
            if (!error) {
                removeElement('wm' + file.filename);
                delete imgthumbnails[file.filename];
                for (let i = 0; i < bsPhotoSelectors.length; i++) {
                    if ($(bsPhotoSelectors[i]).val() == file.filename) {
                        $(bsPhotoSelectors[i]).val("none").change();
                    }
                    $(bsPhotoSelectors[i] + " option[value='" + file.filename + "']").remove();
                } 
                for (let i = 0; i < tBlocks.length; i++) {
                    if (tBlocks[i].includes("photo")) {
                        var block = i + 1;
                        removeElement('tbthumbb' + block + file.filename);
                    }
                } 
            }
        },
        onpreparefile: (file, output) => {
            var canvas = document.getElementById('hiddencanvas');
            var ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            var img = new Image();

            img.onload = function () {
                var scale = 100 / img.height;
                var newwidth = img.width * scale;
                canvas.width = newwidth;
                ctx.drawImage(img, 0, 0, img.width, img.height, 0, 0, newwidth, 100);
                imgthumbnails[file.filename] = canvas.toDataURL();

                for (let i = 0; i < tBlocks.length; i++) {
                    if (tBlocks[i].includes("photo")) {
                        var block = i + 1;
                        var element = document.getElementById(tBlocks[i]);
                        var newHTML = '<div id="tbthumbb' + block + file.filename + '" class="tbthumbcontainer">';
                        newHTML += '<img class="bsImgThmb" src="' + imgthumbnails[file.filename] + '">';
                        newHTML += '<input type="checkbox" id="tb' + block + file.filename + '" name="imgcheckbox' + block + '" value="' + file.filename + '">'
                        newHTML += '<label for="tb' + block + file.filename + '">' + file.filename + '</label></div><br>';
                        element.innerHTML += newHTML;
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
    });

    form.addEventListener('submit', (event) => {
        //check all errors
        var error = false;
        var errormsg = '';
        var attachedimages = false;
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
                        attachedimages = true;
                        var imgcheckboxes = document.getElementsByName("imgcheckbox" + block);
                        var checked = false;
                        for (let j = 0; j < imgcheckboxes.length; j++) {
                            checked = checked || imgcheckboxes[j].checked;
                        }
                        if (!checked) {
                            errormsg += 'Tumblr photo block #' + block + ' has no chosen photos.</br>';
                            error = true;
                        }
                    } else if (tBlocks[i].includes("text")) {
                        if (tTextError[block]) {
                            errormsg += 'Tumblr text block #' + block + ' is over the character limit.</br>';
                            error = true;
                        }
                    }
                }
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
                    attachedimages = true;
                }
            } 
        }
        if ($('#images').is(':checked') && !attachedimages) {
            errormsg += 'Image post has no images attached to post or skeet(s)</br>';
            error = true;
        }



        if (error) {
            $('#errormessages').html(errormsg);
            event.preventDefault();
            return false;
        }
    });
});

function addImgOptions(dropdown) {
    dropdown.innerHTML = '<option value="none">None</option>';
    for (const key in imgthumbnails) {
        dropdown.innerHTML += '<option value="' + key + '">' + key + '</option>';
    }
};

function addThumbnail(option, thumb) {
    const thumbnail = thumb.previousElementSibling;
    if (option != "none") {
        thumbnail.hidden = false;
        thumbnail.src = imgthumbnails[option];
    } else {
        thumbnail.hidden = true;
    }
};

function getImgOptionCheckboxes(elementname) {
    const element = document.getElementById(elementname);
    element.innerHTML = '';

    for (const key in imgthumbnails) {
        var newHTML = '<div id="tbthumbb' + tBlockIndex + key + '" class="tbthumbcontainer">';
        newHTML += '<img class="bsImgThmb" src="' + imgthumbnails[key] + '">';
        newHTML += '<input type="checkbox" id="tb' + tBlockIndex + key + '" name="imgcheckbox' + tBlockIndex + '" value="' + key + '">'
        newHTML += '<label for="tb' + tBlockIndex + key + '">' + key + '</label></div><br>';
        element.innerHTML += newHTML;
    }
};

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
    $('#tbtype' + tBlockIndex).val(blocktype);
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
            getImgOptionCheckboxes('tbphoto' + tBlockIndex);
            break;
        case "link":
            $('#tblock' + tBlockIndex).append('<label for="tblink' + bsPostIndex + 'url">url:</label><input type="url" id="tblink' + bsPostIndex + 'url" name="tblink' + bsPostIndex + 'url" placeholder="https:\/\/example.com\/" class="form-control" required>');
            break;
        case "audio":
            $('#tblock' + tBlockIndex).append('<label for="tbaudio' + bsPostIndex + 'url">url:</label><input type="url" id="tbaudio' + bsPostIndex + 'url" name="tbaudio' + bsPostIndex + 'url" placeholder="https:\/\/example.com\/" class="form-control" required>');
            $('#tblock' + tBlockIndex).append('<label for="tbaudio' + bsPostIndex + 'embed">Embed HTML Code:</label><input type="text" id="tbaudio' + bsPostIndex + 'embed" name="tbaudio' + bsPostIndex + 'embed" class="form-control">');
            break;
        case "video":
            $('#tblock' + tBlockIndex).append('<label for="tbvideo' + bsPostIndex + 'url">url:</label><input type="url" id="tbvideo' + bsPostIndex + 'url" name="tbvideo' + bsPostIndex + 'url" placeholder="https:\/\/example.com\/" class="form-control" required>');
            $('#tblock' + tBlockIndex).append('<label for="tbvideo' + bsPostIndex + 'embed">Embed HTML Code:</label><input type="text" id="tbvideo' + bsPostIndex + 'embed" name="tbvideo' + bsPostIndex + 'embed" class="form-control">');
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

