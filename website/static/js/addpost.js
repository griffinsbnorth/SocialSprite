//error tags
var bsImgError = false;
var bsTextError = {};

//post variables
var bsPostIndex = 1;
var tBlockIndex = 0;
var richTxtEditors = {};
var bsrichTxtEditors = {};
var imgthumbnails = {};
var bstoolbarOptions;
var bsoptions;

$(document).ready(function () {
    //checkboxes
    $('#images').on('change', function () { toggleSection('images', 'imgsection') });
    $('#tumblr').on('change', function () { toggleSection('tumblr', 'tform') });
    $('#bluesky').on('change', function () { toggleSection('bluesky', 'bsform') });

    //image section
    // register the plugins with FilePond
    FilePond.registerPlugin(
        FilePondPluginImagePreview,
        FilePondPluginImageResize,
        FilePondPluginImageTransform,
        FilePondPluginFileRename
    );
    const inputElement = document.getElementById('imgupload');
    const pond = FilePond.create(inputElement, {
        imageResizeTargetHeight: 1290,
        imageResizeTargetWidth: 1280,
        imageResizeMode: 'contain',
        imageResizeUpscale: false,
        storeAsFile: true,
        allowReorder: true
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
                bsImgError = true;
                $('#bsimgerror').removeAttr('hidden');
            }
        },
        onremovefile: (error, file) => {
            if (!error) {
                removeElement('wm' + file.filename);
                bsImgError = true;
                $('#bsimgerror').removeAttr('hidden');
                delete imgthumbnails[file.filename];
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
    $('#bsimgerror').click(function () { hideAndClearError(this) });
    $('#addBStxtBtn').click(function () { addBStext() });
    $('#removeBStxtBtn').click(function () { removeBStext() });
    $('#bsp1i1').on('change', function () { addThumbnail(this.value, this) });
    $('#bsp1i2').on('change', function () { addThumbnail(this.value, this) });
    $('#bsp1i3').on('change', function () { addThumbnail(this.value, this) });
    $('#bsp1i4').on('change', function () { addThumbnail(this.value, this) });
    $('#bsp1i1').on('focus', function () { addImgOptions(this) });
    $('#bsp1i2').on('focus', function () { addImgOptions(this) });
    $('#bsp1i3').on('focus', function () { addImgOptions(this) });
    $('#bsp1i4').on('focus', function () { addImgOptions(this) });

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
    var i = 0;
    for (const key in imgthumbnails) {
        var newHTML = '<div id="tbthumbb' + tBlockIndex + 'i' + i + '" class="tbthumbcontainer">';
        newHTML += '<img class="bsImgThmb" src="' + imgthumbnails[key] + '">';
        newHTML += '<input type="checkbox" id="tb' + tBlockIndex + key + '" name="imgcheckbox" value="' + key + '">'
        newHTML += '<label for="tb' + tBlockIndex + key + '">' + key + '</label></div><br>';
        element.innerHTML += newHTML;
        i += 1;
    }
};

function hideAndClearError(errorElement) {
    errorElement.hidden = true;
    bsImgError = false;
};

function toggleSection(val, section) {
    const formCheckbox = document.getElementById(val);
    const formSection = document.getElementById(section);
    const submit = document.getElementById('submitBtn');

    formSection.hidden = !formCheckbox.checked;
    submit.disabled = !formCheckbox.checked;
};

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
        $('#bsp' + bsPostIndex + 'i' + i).on('focus', function () { addImgOptions(this) });
    }
    $('#bspost' + bsPostIndex).append('<div id="bstext' + bsPostIndex + '" name="bstext"></div>');
    bsrichTxtEditors[bsPostIndex] = new Quill('#bstext' + bsPostIndex, bsoptions);
    bsrichTxtEditors[bsPostIndex].on('text-change', (delta, oldDelta, source) => {
        countChar(bsPostIndex, '#charNum' + bsPostIndex);
    });
    $('#bspost' + bsPostIndex).append('<div id="charNum' + bsPostIndex + '" class="charNum">0/300</div>');
};

function removeBStext() {
    removeElement('bspost' + bsPostIndex);
    delete richTxtEditors[bsPostIndex];
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
            richTxtEditors[tBlockIndex] = new Quill('#tbtext' + tBlockIndex, options);
            break;
        case "photo":
            $('#tblock' + tBlockIndex).append('<div id="tbphoto' + tBlockIndex + '" name="tbphoto" class="tbphoto"></div>');
            getImgOptionCheckboxes('tbphoto' + tBlockIndex);
            $('#tblock' + tBlockIndex).append('<button type="button" class="btn btn-secondary" onclick="getImgOptionCheckboxes(\'tbphoto' + tBlockIndex + '\')">Refresh Image Options</button>');
            break;
        case "link":
            $('#tblock' + tBlockIndex).append('<label for="tblink' + bsPostIndex + 'url">url:</label><input type="url" id="tblink' + bsPostIndex + 'url" name="tblink' + bsPostIndex + 'url" placeholder="https:\/\/example.com\/" class="form-control">');
            break;
        case "audio":
            $('#tblock' + tBlockIndex).append('<label for="tbaudio' + bsPostIndex + 'url">url:</label><input type="url" id="tbaudio' + bsPostIndex + 'url" name="tbaudio' + bsPostIndex + 'url" placeholder="https:\/\/example.com\/" class="form-control">');
            $('#tblock' + tBlockIndex).append('<label for="tbaudio' + bsPostIndex + 'embed">Embed HTML Code:</label><input type="text" id="tbaudio' + bsPostIndex + 'embed" name="tbaudio' + bsPostIndex + 'embed" class="form-control">');
            break;
        case "video":
            $('#tblock' + tBlockIndex).append('<label for="tbvideo' + bsPostIndex + 'url">url:</label><input type="url" id="tbvideo' + bsPostIndex + 'url" name="tbvideo' + bsPostIndex + 'url" placeholder="https:\/\/example.com\/" class="form-control">');
            $('#tblock' + tBlockIndex).append('<label for="tbvideo' + bsPostIndex + 'embed">Embed HTML Code:</label><input type="text" id="tbvideo' + bsPostIndex + 'embed" name="tbvideo' + bsPostIndex + 'embed" class="form-control">');
    }
};

function removeTblock() {
    removeElement('tblock' + tBlockIndex);
    if (richTxtEditors[tBlockIndex] != null) {
        delete richTxtEditors[tBlockIndex];
    }
    tBlockIndex -= 1;
    if (tBlockIndex == 0) {
        $('#removeTblockBtn').prop('hidden', true);
    }
};

