def file_load(path: str) -> str:
    """
    Load a file and return its content as a string.
    :param path: Path to the file
    :return: Content of the file
    """
    with open(path, 'r') as file:
        return file.read()
