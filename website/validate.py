def validatetextfield(fieldname, text, maxlength, minlength = 0):
    message = ''
    status = True
    if len(text) <= minlength:
        message = fieldname + ' too short.'
        status = False
    elif len(text) > maxlength:
        message = fieldname + ' too long.'
        status = False

    return {'status': status,'message': message}

def sanitize_input(user_input):
    return re.sub(r'[^\w\s]', '', user_input)  # Removes special characters