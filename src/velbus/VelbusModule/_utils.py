import sanic.response


def validate_channel_from_pathinfo(path_info, max_channel):
    if len(path_info) == 0:
        return sanic.response.text('\r\n'.join(map(str, range(1, max_channel+1))) + '\r\n')

    if len(path_info) > 1:
        return sanic.response.text('Not Found', 404)

    if int(path_info[0]) not in range(1, max_channel+1):
        return sanic.response.text('Not Found', 404)

    return None
