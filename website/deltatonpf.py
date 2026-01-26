#https:#github.com/jfhr/deltaconvert/tree/main
#Converted js from this project to python
import copy

class DeltaInsertOperation():
    def __init__(self, insert: str, attributes={}):
        self.insert = insert
        self.attributes = attributes

class DeltaObj():
    def __init__(self, ops: DeltaInsertOperation):
        self.ops = ops

#Represents a block-level insert element with formatting
#property {InlineInsert[]} children
#property {Object.<string, *>} attributes
class BlockInsert():
    def __init__(self, attributes={}):
        self.children = []
        self.attributes = attributes


#Represents some inline content (text or embed) with formatting.
#An inline insert is always the child of a block insert.
#property {(string|Object.<string, *>)} insert
#property {Object.<string, *>} attributes
class InlineInsert():
    def __init__(self, insert, attributes={}):
        self.insert = insert
        self.attributes = attributes

class DeltaToIntermediateOptions():
    def __init__(self, mergeAdjacentCodeBlocks = True):
        self.mergeAdjacentCodeBlocks = mergeAdjacentCodeBlocks

DEFAULT_OPTIONS = { 'mergeAdjacentCodeBlocks': True }

#Convert a quill delta to our intermediate format.
#param delta
#param options {DeltaToIntermediateOptions}
#return {BlockInsert[]}
def deltaToIntermediate(delta, options = DEFAULT_OPTIONS):
    blocks = []

    for opIndex, opp in enumerate(delta.ops):
        att = {}
        if 'attributes' in opp:
            att = opp['attributes']
        op = DeltaInsertOperation(opp['insert'],att)
        if isinstance(op.insert, str):
            # Test if string is only newline characters
            if '\n' in op.insert and op.insert.isspace():
                #Handle block-level formatting for previous line of text
                if not blocks:
                    blocks.append(BlockInsert(copy.deepcopy(op.attributes)))
                else:
                    blocks[-1].attributes = {**blocks[-1].attributes, **op.attributes}
                    blocks.append(BlockInsert())
            elif '\n' in op.insert:
                #Handle one or multiple paragraphs of text.
                #Note that the following insert might include additional block-level formatting for the last paragraph
                paras = op.insert.split('\n')

                #First paragraph might still belong to previous block
                if paras[0] and blocks:
                    blocks[-1].children.append(InlineInsert(paras.pop(0), copy.deepcopy(op.attributes)))

                for paraIndex, paragraph in enumerate(paras):
                    if paragraph:
                        blocks.append(BlockInsert(copy.deepcopy(op.attributes)))
                        blocks[-1].children.append(InlineInsert(paragraph, copy.deepcopy(op.attributes)))
                    #Fix #11: if this block insert ends in newlines, add a newline to the start of the next block
                    #to make sure there's a paragraph break between the two blocks.
                    elif paraIndex == len(paras) - 1 and len(delta.ops) > opIndex + 1:
                        if isinstance(delta.ops[opIndex + 1]['insert'], str):
                            delta.ops[opIndex + 1]['insert'] = '\n' + delta.ops[opIndex + 1]['insert']

            else:
                #Handle pure inline text
                if not blocks:
                    blocks.append(BlockInsert())
                blocks[-1].children.append(InlineInsert(op.insert, copy.deepcopy(op.attributes)))
        else:
            #Handle embeds
            blocks.append(BlockInsert(copy.deepcopy(op.attributes)))
            blocks[-1].children.append(InlineInsert(op.insert, copy.deepcopy(op.attributes)))

    #Normally we need block-level tags (e.h. <p>) to create linebreaks.
    #But code blocks are wrapped in the <pre> tag, meaning that plain newlines are preserved.
    #So two adjacent <pre> blocks can be merged in one with a newline in between.
    if options['mergeAdjacentCodeBlocks']:
        blocks = mergeAdjacentCodeBlocks(blocks)

    return blocks

#param blocks {BlockInsert[]}
def mergeAdjacentCodeBlocks(blocks):
    i = 0
    while i < len(blocks) - 1:
        if blocks[i].attributes['code-block'] and blocks[i + 1].attributes['code-block']:
            blocks[i].children.extend(blocks[i + 1].children)
            blocks.pop(i + 1)
            #Decrement index since the array has been changed
            i -= 1
        i += 1
    return blocks




#Tumblr NPF object.
#content: NpfContent[]
class NpfObj():
    def __init__(self, content):
        self.content = content 

#Tumblr NPF content object.
#formatting: NpfFormatting[]
class NpfContent():
    def __init__(self, npftype: str, subtype = '', text = '', url = '', indent_level = None, formatting = [], media = {}):
        self.type = npftype 
        self.subtype = subtype
        self.text = text 
        self.url = url
        self.indent_level = indent_level
        self.formatting = formatting
        self.media = media
    
    def to_dict(self):
        content = {}
        content['type'] = self.type
        if self.subtype:
            content['subtype'] = self.subtype
        if self.text:
            content['text'] = self.text
        if self.url:
            content['url'] = self.url
        if self.indent_level:
            content['indent_level'] = self.indent_level
        if self.formatting:
            formattinglist = []
            for item in self.formatting:
                formattinglist.append(item.to_dict())

            content['formatting'] = formattinglist
        if self.media:
            content['media'] = self.media

        return content

#Tumblr NPF formatting object.
class NpfFormatting():
    def __init__(self, start: int, end: int, npftype: str, url = '', npfhex = '', blog = ''):
        self.start = start 
        self.end = end
        self.type = npftype 
        self.url = url
        self.hex = npfhex 
        self.blog = blog

    def to_dict(self):
        content = {}
        content['start'] = self.start
        content['end'] = self.end
        content['type'] = self.type
        if self.url:
            content['url'] = self.url
        if self.hex:
            content['hex'] = self.hex
        if self.blog:
            content['blog'] = self.blog

        return content

#@summary Convert a quill delta to tumblr's NPF format.
#@description Converts formatted text, links, images.
#For images, extra attributes like original_size are ignored,
#only the image url is used.
#Videos and other embeds aren't currently supported.
#Tumblr NPF only supports heading levels 1 and 2. Headings
#of level >= 3 will be converted to bold text.
#@param delta {DeltaObj}
#@return {NpfObj}
def deltaToNpf(delta):
    blocks = deltaToIntermediate(delta, {'mergeAdjacentCodeBlocks': False})

    #type NpfContent[]
    npf = []

    for block in blocks:
        # Skip blocks with no children and no formatting
        if not block.children and not block.attributes:
            continue

        text = ''
        #type NpfFormatting[]
        formatting = []

        for inline in block.children:
            # Handle text with inline formatting
            if isinstance(inline.insert, str):
                start = len(text)
                text += inline.insert
                end = len(text)
                first = inline.insert[0]

                if first == '@' and 'link' in inline.attributes:
                    blogname = inline.attributes['link'].replace('@', '').strip()
                    formatting.append(NpfFormatting(start, end, npftype = 'mention', blog = blogname))
                else:
                    if 'bold' in inline.attributes:
                        formatting.append(NpfFormatting(start, end, npftype = 'bold' ))
                    if 'italic' in inline.attributes:
                        formatting.append(NpfFormatting(start, end, npftype = 'italic' ))
                    if 'strike' in inline.attributes:
                        formatting.append(NpfFormatting(start, end, npftype = 'strikethrough' ))
                    if 'color' in inline.attributes:
                        formatting.append(NpfFormatting(start, end, npftype = 'color', npfhex = inline.attributes['color'] ))
                    if 'link' in inline.attributes:
                        formatting.append(NpfFormatting(start, end, npftype = 'link', url = inline.attributes['link'] ))
                    if 'code' in inline.attributes:
                        formatting.append(NpfFormatting(start, end, color = '#e83e8c' ))

            # Handle embeds (e.g. images) directly
            elif 'image' in inline.insert:
                npf.append(NpfContent(npftype=guessImageMimeType(inline.insert['image']),url=inline.insert['image']).to_dict())
            elif 'video' in inline.insert:
                npftype = guessVideoMimeType(inline.insert['video'])
                # Can't determine type, use the url directly instead
                if npftype == 'video':
                    npf.append(NpfContent(npftype='video',url=inline.insert['video']).to_dict())
                else:
                    media = {
                        'url' : inline.insert['video'], 
                        'type' : npftype 
                        }
                    npf.append(NpfContent(npftype='video', media = media).to_dict())

        if text:
            #@type {NpfContent}
            content = NpfContent(npftype= 'text', text = text);

            # Tumblr only supports heading 1 and 2
            if 'header' in block.attributes:
                if block.attributes['header'] == 1:
                    content.subtype = 'heading1'
                elif block.attributes['header'] == 2:
                    content.subtype = 'heading2'
                elif block.attributes['header'] > 2:
                    # Lower levels are converted to bold text. Use
                    # unshift() here instead of append() bc we expect
                    # formatting to be ordered by start index.
                    formatting.insert(0,NpfFormatting(0, len(text), npftype = 'bold'))
            elif 'blockquote' in block.attributes:
                content.subtype = 'indented'
            elif 'list' in block.attributes:
                if block.attributes['list'] == 'ordered':
                    content.subtype = 'ordered-list-item'
                else:
                    content.subtype = 'unordered-list-item'
            elif 'code-block' in block.attributes:
                content.subtype = 'chat'

            if 'indent' in block.attributes:
                content.indent_level = block.attributes['indent'];

            formatting = mergeFormatting(formatting)
            if formatting:
                content.formatting = formatting

            npf.append(content.to_dict())

    return {'content': npf}

#Guess image MIME type based on url file extension.
#If unsuccessful, returns 'image'
#@param url {string}
#@return {string}
def guessImageMimeType(url):
    url = url.lower()
    if url.endswith('.jpg') or url.endswith('.jpeg'):
        return 'image/jpg'
    if url.endswith('.png'):
        return 'image/png'
    if url.endswith('.gif'):
        return 'image/gif'
    return 'image'

# Guess video MIME type based on url file extension.
# If unsuccessful, returns 'video'
# param url {string}
# return {string}
def guessVideoMimeType(url):
    url = url.lower()
    if url.endswith('.mp4'):
        return 'video/mp4'
    if url.endswith('.webp'):
        return 'video/webp'
    if url.endswith('.ogg'):
        return 'video/ogg'
    return 'video'

#Looks for multiple equivalent overlapping formatting entries
# and merges them into one.
# This assumes that entries are ordered by start index.
#param formatting {NpfFormatting[]}
def mergeFormatting(formatting):
    i = 0
    while i < len(formatting):
        j = i + 1
        while j < len(formatting):
            if formatting[i].end >= formatting[j].start and areEquivalent(formatting[i], formatting[j]):
                formatting[i].end = max(formatting[i].end, formatting[j].end)
                formatting.pop(j)
            else:
                j += 1
        i += 1

    return formatting

#param f1 {NpfFormatting}
#param f2 {NpfFormatting}
#return {boolean}
def areEquivalent(f1, f2):
    if f1.type != f2.type:
        return False
    if f1.type == 'link' and f1.url != f2.url:
        return False
    if f1.type == 'mention' and f1.blog['uuid'] != f2.blog['uuid']:
        return False
    #noinspection RedundantIfStatementJS
    if f1.type == 'color' and f1.hex != f2.hex:
        return False
    return True