def attr_name_from_file_to_object(attr_name: str) -> str:
    if attr_name in ["type", "id"]:
        return attr_name + "_"
    return attr_name


def attr_name_from_object_to_file(attr_name: str) -> str:
    if attr_name in ["type_", "id_"]:
        return attr_name[:-1]
    return attr_name
