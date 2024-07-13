import logging
def create_logger(name, level=20):
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(level)

    # create console handler and set level to debug
    stream = logging.StreamHandler()
    stream.setLevel(level)

    # create formatter
    stream_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add formatter to ch
    stream.setFormatter(stream_format)

    # add ch to logger
    logger.addHandler(stream)

    # Facebook prophet breaks logger without this line:
    # https://stackoverflow.com/q/56461631/4672992
    logger.propagate = False
    return logger